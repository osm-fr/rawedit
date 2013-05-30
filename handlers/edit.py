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

import os
from mod_python import apache, util

def handler(req, session):
    session.authorize()
    
    req.content_type = "text/html"
    
    osm_type = req.uri.split("/")[2]
    osm_id   = req.uri.split("/")[3]
    
    if osm_id == "create":
        actions = '<a accesskey="S" href="javascript:ApiPut();">create</a>'
    else:
        actions = '<a accesskey="S" href="javascript:ApiPut();">update</a> - <a href="javascript:ApiDel();">delete</a>'
        
    data = open(os.path.join(req.document_root(),"main.tpl")).read()
    data = data.replace('?osm_type?', osm_type)
    data = data.replace('?osm_id?', osm_id)
    data = data.replace('?actions?', actions)

    req.write(data)

    return apache.OK
