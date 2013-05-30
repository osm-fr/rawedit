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
import sys, httplib, xml.etree.cElementTree as ET

tpl_node = '<node lat="#" lon="#">\n  <tag k="#" v="#" />\n</node>'
tpl_way  = '<way>\n  <nd ref="#" />\n  <nd ref="#" />\n  <nd ref="#" />\n  <tag k="#" v="#" />\n</way>'
tpl_rel  = '<relation>\n  <member type="node|way|relation" ref="#" role="" />\n  <member type="node|way|relation" ref="#" role="" />\n  <member type="node|way|relation" ref="#" role="" />\n  <tag k="#" v="#" />\n</relation>'

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
    
    osm_type   = req.uri.split("/")[2]
    osm_id     = req.uri.split("/")[3]
    osm_uri    = "/api/0.6/%s/%s"%(osm_type,osm_id)
    
    if osm_id=="create":
        if osm_type=="node":
            req.write(tpl_node)
        if osm_type=="way":
            req.write(tpl_way)
        if osm_type=="relation":
            req.write(tpl_rel)
        return apache.OK

    conn = httplib.HTTPConnection(session.get('oauth_server'))
    conn.putrequest("GET", osm_uri)
    conn.endheaders()
    
    resp = conn.getresponse()
    res_status = resp.status
    res_data   = resp.read()
    
    if res_status == 200:
        xml_data = ET.fromstring(res_data)
        xml_data = xml_data.getchildren()[0]
        for k in ["timestamp", "user", "uid", "visible", "changeset"]:
            if k in xml_data.attrib:
                xml_data.attrib.pop(k)
        xml_data = ET.tostring(xml_data).strip()
        for line in xml_data.split("\n"):
            line = unescape(line.strip()).encode("utf8")
            #line = line.strip().encode("utf8")
            if line.split(" ")[0] in ["<node","<way","<relation","</node>","</way>","</relation>"]:
                req.write(line+"\n")
            else:
                req.write("  "+line+"\n")
    else:
        req.write("Error " + str(res_status) + " (%s)\n"%resp.reason)

    return apache.OK
