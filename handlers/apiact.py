#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Etienne Chové <chove@crans.org> 2009                       ##
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
import sys, httplib, xml.etree.cElementTree as ET, apiget

###########################################################################
## source : http://effbot.org/zone/re-sub.htm
import re, htmlentitydefs
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text
    return re.sub("&#?\w+;", fixup, text)
###########################################################################

def handler(req, session):

    req.content_type = "text/plain"

    action     = req.uri.split("/")[1]
    osm_type   = req.uri.split("/")[2]
    osm_id     = req.uri.split("/")[3]
    osm_uri    = "/api/0.6/%s/%s"%(osm_type,osm_id)

    form       = util.FieldStorage(req)
    osm_data   = form.get("osm_data", "")
    osm_chgset = str(session.get('changeset'))

    # parse data
    try:
        xml_data = ET.fromstring("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"+osm_data)
        if xml_data.tag == u"osm":
            xml_data = xml_data.getchildren()[0]
    except:
        req.write("<font color=\"#FF0000\">XML parser can't parse this data</font>\n")
        req.write(osm_data)
        return apache.OK

    # update data
    xml_data.attrib["changeset"] = osm_chgset
    tosend  = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    tosend += "<osm version=\"0.6\">\n"
    tosend += ET.tostring(xml_data)
    tosend += "</osm>\n"

    # send data
    httpconn      = httplib.HTTPConnection('%s:%d'%(session.get('oauth_server'),session.get('oauth_port')))
    consumer      = session.liboauth.OAuthConsumer(session.get('consumer_key'), session.get('consumer_secret'))
    signmeth      = session.liboauth.OAuthSignatureMethod_HMAC_SHA1()
    access_token  = session.liboauth.OAuthToken(session.get("access_token_key"), session.get("access_token_secret"))
    oauth_request = session.liboauth.OAuthRequest.from_consumer_and_token(consumer, token=access_token, http_method={'apiput':'PUT','apidel':'DELETE'}[action], http_url='http://%s%s'%(session.get('oauth_server'), osm_uri))
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

    if res_status == 200:
        if osm_id=='create':
            req.write("<font color=\"#009900\">Successfull create.</font><br>Go to <a href=\"/edit/%s/%s\">%s/%s</a> to modify it.\n"%(osm_type,res_data,osm_type,res_data))
            return apiget.handler(req, session)
        if action=='apiput':
            req.write("<font color=\"#009900\">Successfull update.</font>\n")
            return apiget.handler(req, session)
        if action=='apidel':
            req.write("<font color=\"#009900\">Successfull delete.</font>\n")
            return apiget.handler(req, session)
    else:
        req.write("<font color=\"#FF0000\">API returns Error" + str(res_status) + " " + resp.reason + ".</font>\n")
        return apiget.handler(req, session)
