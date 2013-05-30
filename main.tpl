<html>

<head>
  <style type="text/css">
  table
  {
    border-width: 1px 1px 1px 1px;
    border-style: solid;
    border-collapse: collapse;
  }
  td
  {
    border-width: 1px 1px 1px 1px;
    border-style: solid;
    margin: 0px;
    padding: 5px;
  }
  a:link {
    color: black;
  }
    a:visited {
    color: black;
  }
    a:hover {
    color: black;
  }
  </style>
</head>

<body bgcolor="#FFFFFF">

  <script type="text/javascript">

  var osm_type = '?osm_type?';
  var osm_id   = '?osm_id?';
  
  function ApiGet()
  {
    var myReq = new XMLHttpRequest();
    document.getElementById('osm_data').value    = '';
    document.getElementById('osm_msg').innerHTML = '';
    if (myReq) {
      myReq.onreadystatechange = function (evnt) { if(myReq.readyState == 4) {
        document.getElementById('osm_data').value = myReq.responseText;
      } }
      myReq.open('GET', '/apiget/' + osm_type + '/' + osm_id, true);
      myReq.send('');
    }
  }
    
  function ApiPut()
  {
    ApiDo('apiput');
  }
  
  function ApiDel()
  {
    ApiDo('apidel');
  }
 
  function ApiDo(action)
  {
    var myReq = new XMLHttpRequest();
    if (myReq) {
      myReq.onreadystatechange = function (evnt) { if(myReq.readyState == 4) {
        res = myReq.responseText.split('\n');
        document.getElementById('osm_msg').innerHTML = res[0];
	tmp = res.shift();
	document.getElementById('osm_data').value    = res.join('\n');
	} }
      myReq.open('POST', '/' + action + '/' + osm_type + '/' + osm_id, true);
      myReq.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
      poststr = "osm_data=" + encodeURIComponent(document.getElementById("osm_data").value );
      myReq.send(poststr);
    }  
  }
  
  </script>

  <!--<font size="+4" color="#FF0000"><b>! ! ! dev api data ! ! !</b></font><br>-->

  <table bgcolor="#EEEEEE">
  <tr id="uploader1">
    <td width="80">
      <b>Data</b>
    </td>
    <td>
      <div id="osm_msg"></div>
      <textarea id="osm_data" cols="80" rows="20" wrap="off" style="overflow:auto;"></textarea>
    </td>
  </tr>
  <tr id="uploader2">
    <td>
      <b>Actions</b>
    </td>
    <td>
      ?actions?
    </td>
  </tr>
</table>
  
</body>

  <script type="text/javascript">
    ApiGet();
  </script>

</html>
