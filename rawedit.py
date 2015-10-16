#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Etienne Chové <chove@crans.org> 2010                       ##
##                                                                       ##
## This program is free software: you can redistribute it and/or modify  ##
## it under the terms of the GNU General Public License as published by  ##
## the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                   ##
##                                                                       ##
## This program is distributed in the hope that it will be useful,       ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of        ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         ##
## GNU General Public License for more details.                          ##
##                                                                       ##
## You should have received a copy of the GNU General Public License     ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>. ##
##                                                                       ##
###########################################################################


from mod_python import apache, util
import sys, os, re, httplib, cgi, base64, httplib, Cookie, datetime, liboauth, random
import xml.etree.cElementTree as ET
import psycopg2

root = sys.path.append(os.path.dirname(__file__))

OAUTH_SERVER      = 'www.openstreetmap.org'
CONSUMER_KEY      = 'xxx'
CONSUMER_SECRET   = 'xxx'

#OAUTH_SERVER      = 'api06.dev.openstreetmap.org'
#CONSUMER_KEY      = 'xxx'
#CONSUMER_SECRET   = 'xxx'

OAUTH_PORT        = 80
REQUEST_TOKEN_URL = 'http://%s/oauth/request_token'%OAUTH_SERVER
ACCESS_TOKEN_URL  = 'http://%s/oauth/access_token'%OAUTH_SERVER
AUTHORIZATION_URL = 'http://%s/oauth/authorize'%OAUTH_SERVER
PGSQL_DBSTRING    = 'host=localhost user=rawedit password=xxx'
PGSQL_DATABASE    = 'rawedit'

sys.path.append(root)
from handlers import apiget as handler_apiget
from handlers import apiact as handler_apiact
from handlers import edit as handler_edit

################################################################################
## handler debug

def handler_debug(req):
    req.content_type = "text/plain"

    req.write("%s\n"%req.document_root())
    
    req.write("A----------------------------\n")
    req.write(str(req.args)+"\n")
    
    req.write("B----------------------------\n")
    for k in req.headers_in:
        req.write("%s = %s\n"%(k, repr(req.headers_in[k])))
    
    req.write("C----------------------------\n")
    for k in dir(apache):
        req.write("%s = %s\n"%(k, eval("apache.%s"%k)))
    
    req.write("D----------------------------\n")
    for k in dir(req):
        req.write("%s = %s\n"%(k, eval("req.%s"%k)))
            
    return apache.OK

################################################################################
## session manager

class session_manager:
    
    _keys = ['request_token_key','request_token_secret','access_token_key','access_token_secret','data_changeset','data_uri']
    liboauth = liboauth
    
    def __init__(self, req):
        """ Initialise session """
        
        self._req    = req
        self._pgconn = psycopg2.connect(PGSQL_DBSTRING, PGSQL_DATABASE)
        self._pgcurs = self._pgconn.cursor()
        self._sessid = self._getsessionid(req.uri.split("/")[1]=="logout")
        
    def _getsessionid(self, logout):
        """ Return session id and create it if needed """

        # id generator
        def makeid(size=64):
            chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            res = ""
            for i in range(size):
                res += chars[int(random.uniform(0, len(chars)))]
            return res
        
        # get session in cookie
        if "Cookie" in self._req.headers_in:
            cki = Cookie.SimpleCookie()
            cki.load(self._req.headers_in["Cookie"])
            if "session" in cki:
                sessionid = cki.get("session").value
                self._pgcurs.execute("SELECT id FROM session WHERE id = '%s';"%sessionid)
                pgres = self._pgcurs.fetchone()
                if pgres:
                    if logout:
                        self._pgcurs.execute("DELETE FROM session WHERE id = '%s';"%sessionid)
                        self._pgconn.commit()
                    else:
                        return sessionid
        
        # create new session id
        while True:
            sessionid = makeid()
            self._pgcurs.execute("SELECT id FROM session WHERE id = '%s';"%sessionid)
            if not self._pgcurs.fetchone():
                
                # register session
                self._pgcurs.execute("INSERT INTO session (date, id) VALUES (NOW(), '%s');"%sessionid)
                self._pgconn.commit()
                
                # add cookie
                cki = Cookie.SimpleCookie()
                cki["session"] = sessionid
                cki["session"]['expires'] = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d %b %Y %H:00:00 GMT")
                cki["session"]['path']    = '/'
                self._req.headers_out["Set-Cookie"] = str(cki).split(":", 1)[1][1:]
                
                # return new session id
                return sessionid
    
    def authorize(self):
        
        # already authorized
        if self.get('request_token_key') and self.get('access_token_key'):
            return
        
        # connections to oauth server
        httpconn = httplib.HTTPConnection('%s:%d'%(self.get('oauth_server'), self.get('oauth_port')))
        consumer = liboauth.OAuthConsumer(self.get('consumer_key'), self.get('consumer_secret'))
        signmeth = liboauth.OAuthSignatureMethod_HMAC_SHA1()
        
        # get request token
        oauth_request = liboauth.OAuthRequest.from_consumer_and_token(consumer, http_url=REQUEST_TOKEN_URL)
        oauth_request.sign_request(signmeth, consumer, None)
        httpconn.putrequest(oauth_request.http_method, oauth_request.http_url)
        for k, v in oauth_request.to_header().items():
            httpconn.putheader(k, v)
        httpconn.putheader('Content-Length', 0)
        httpconn.endheaders()
        data  = httpconn.getresponse().read()
        token = liboauth.OAuthToken.from_string(data)
        self.set('request_token_key', token.key)
        self.set('request_token_secret', token.secret)
    
        # add return uri to row
        self.set('data_uri', self._req.uri)
            
        # authorize token
        util.redirect(self._req, "%s?oauth_token=%s"%(AUTHORIZATION_URL,token.key))
   
    def _get_changeset(self):
        # read from db
        chg_in_db = self.get("data_changeset")
        if not chg_in_db:
            return self._create_changeset()
        # is it closed ?
        conn = httplib.HTTPConnection('%s:%d'%(self.get('oauth_server'), self.get('oauth_port')))
        conn.putrequest("GET", "/api/0.6/changeset/%d"%chg_in_db)
        conn.endheaders()
        resp = conn.getresponse()
        res_status = resp.status
        res_data   = resp.read()
        if res_status <> 200:
            return self._create_changeset()
        xml_data = ET.fromstring(res_data)
        xml_data = xml_data.getchildren()[0]
        if xml_data.attrib["open"] == "false":
            return self._create_changeset()
        # still open
        return int(chg_in_db)
        
    def _create_changeset(self):
        
        osm_uri = "/api/0.6/changeset/create"
        tosend  = ""
        tosend += "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        tosend += "<osm version=\"0.6\"><changeset><tag k=\"created_by\" v=\"RawEdit\" /></changeset></osm>"
        
        # send data
        httpconn      = httplib.HTTPConnection('%s:%d'%(self.get('oauth_server'),self.get('oauth_port')))
        consumer      = liboauth.OAuthConsumer(self.get('consumer_key'), self.get('consumer_secret'))
        signmeth      = liboauth.OAuthSignatureMethod_HMAC_SHA1()
        access_token  = liboauth.OAuthToken(self.get("access_token_key"), self.get("access_token_secret"))
        oauth_request = liboauth.OAuthRequest.from_consumer_and_token(consumer, token=access_token, http_method='PUT', http_url='http://%s%s'%(self.get('oauth_server'), osm_uri))
        oauth_request.sign_request(signmeth, consumer, access_token)
        httpconn.putrequest(oauth_request.http_method, oauth_request.http_url)
        for k, v in oauth_request.to_header().items():
            httpconn.putheader(k, v)
        httpconn.putheader('Content-Length', len(tosend))
        httpconn.endheaders()
        httpconn.send(tosend)
        # download and print data
        resp = httpconn.getresponse()
        res_status = resp.status
        res_data   = resp.read()
        # return changeset id
        self._pgcurs.execute("UPDATE session SET data_changeset=%d WHERE id = '%s';"%(int(res_data), self._sessid))
        self._pgconn.commit()
        return int(res_data)
    
    def get(self, key):
        
        if key=='oauth_server':
            return OAUTH_SERVER
        if key=='oauth_port':
            return OAUTH_PORT
        if key=='consumer_key':
            return CONSUMER_KEY
        if key=='consumer_secret':
            return CONSUMER_SECRET
        if key=='changeset':
            return self._get_changeset()
        
        if key not in self._keys:
            raise KeyError
        self._pgcurs.execute("SELECT %s FROM session WHERE id = '%s';"%(key, self._sessid))
        pgres = self._pgcurs.fetchone()
        return pgres[0]
    
    def set(self, key, value):
        if key not in self._keys:
            raise KeyError
        self._pgcurs.execute("UPDATE session SET %s='%s' WHERE id = '%s';"%(key, value, self._sessid))
        self._pgconn.commit()

def handler_oauthreturn(req, session):
    
    # get an access token
    httpconn = httplib.HTTPConnection("%s:%d" % (OAUTH_SERVER, OAUTH_PORT))
    consumer = liboauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
    signmeth = liboauth.OAuthSignatureMethod_HMAC_SHA1()
    token    = liboauth.OAuthToken(session.get("request_token_key"), session.get("request_token_secret"))
    oauth_request = liboauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_url=ACCESS_TOKEN_URL)
    oauth_request.sign_request(signmeth, consumer, token)
    httpconn.putrequest(oauth_request.http_method, oauth_request.http_url)
    for k, v in oauth_request.to_header().items():
        httpconn.putheader(k, v)
    httpconn.putheader('Content-Length', 0)
    httpconn.endheaders()
    token = liboauth.OAuthToken.from_string(httpconn.getresponse().read())
    session.set('access_token_key', token.key)
    session.set('access_token_secret', token.secret)
    
    # redirect
    util.redirect(req, session.get("data_uri"))
    
################################################################################
##

info = """<html>
<head>
<title>OpenStreetMap RawEditor</title>
</head>
<body>
This server allow you to modify <a hreaf="http://www.openstreetmap.org">OpenStreetMap</a> XML data without any editor.<br>You should use URL such as :
<ul>
<li>http://rawedit.openstreetmap.fr/edit/node/####</li>
<li>http://rawedit.openstreetmap.fr/edit/way/create</li>
</ul>
</body>
</html>
"""

def handler(req):
    
    #return handler_debug(req)
    
    session = session_manager(req)    
    args    = req.uri.split("/")
    
    if args[1] == "apiget":
        return handler_apiget.handler(req, session)
    if args[1] == "apiput":
        return handler_apiact.handler(req, session)    
    if args[1] == "apidel":
        return handler_apiact.handler(req, session)    
    if args[1] == "edit":
        return handler_edit.handler(req, session)
    if args[1] == "oauthreturn":
        return handler_oauthreturn(req, session)
    
    req.content_type = "text/html"
    req.write(info)
    return apache.OK
    
    return apache.HTTP_NOT_FOUND
