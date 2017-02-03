import time, socket
import mock_machine as machine

DEBUG = False
DEBUG = True

pins = [machine.Pin(i, machine.Pin.IN) for i in (0, 2, 4, 5, 12, 13, 14, 15)]

#here are some mocked test settings
pins[0].value = True  #sets pin "0" to high
pins[3].value = True  #sets pin "5" to high


doc_template = """
<!DOCTYPE html>
<html>
    <head> <title>ESP8266 Pins</title> 
    </head>
    <body> <h1>ESP8266 Pins</h1>
        <table border="1"> <tr><th>Pin</th><th>Value</th></tr>{table_content}</table>
        <div>{comment}</div>
    </body>
    {javascript}
</html>
"""

doc_template = doc_template.strip() #remove troublesome leading (and trailing) whitespace

javascript = """
<script>
  document.body.addEventListener("click", function(event) {
    if (event.target.nodeName == "BUTTON"){
      var btn_id = event.target.getAttribute("id")
      console.log("Clicked", btn_id);
      postToggle(btn_id);
    }
  });
  
  function postToggle (btn_id) {
    var form = document.createElement('form');
    form.setAttribute('method', 'post');
    form.setAttribute('action', 'http://0.0.0.0?btn_id='+btn_id);
    form.setAttribute('btn_id', btn_id);
    form.style.display = 'hidden';
    document.body.appendChild(form)
    form.submit();
  }
</script>
"""

row_template = """
<tr>
  <td>{pin_id}</td>
  <td>{pin_value}</td>
  <td>
    <button type="button" id="btn{pin_id}">togggle</button>
  </td>
</tr>
"""

current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

headers_template = [
    "HTTP/1.1 200 OK",
    "Date: %s" % current_date,
    "Server: Simple-Python-HTTP-Server",
    "Content-Length: {content_length}",  #hold this place with a formatter
    "Content-Type: text/html",
    "Connection: close",
    ""  #NOTE blank line needed!
]

headers_template = "\r\n".join(headers_template)

def finalize_document(comment = ""):
    #NOTE this content must be generated dynamically
    rows = [row_template.format(pin_id = str(p),pin_value=p.value()) for p in pins]
    
    rows = ' '.join(rows) #empty line cause row to indent properly
            
    doc = doc_template.format(javascript = javascript,
                              table_content = rows,
                              comment = comment,
                              )
    doc_bytes = bytes(doc,'utf8')
    headers = headers_template.format(content_length = len(doc_bytes)) #now assign the content's length
    header_bytes = bytes(headers,'utf8')
    return (header_bytes, doc_bytes)


addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print('listening on', addr)

    while True:
        try:
            cl, addr = s.accept()
            print("-"*80)
            print('client connected from', addr)
            cl_file = cl.makefile('rwb', 0)
            #parse the request header
            header_line = str(cl_file.readline(),'utf8').strip()
            _, req, protocol = header_line.split()
            #split off any params if they exist
            req = req.split("?")
            req_file = req[0]
            params = {}
            if len(req) == 2:
                pairs = req[1].split("&")
                params = dict(pair.split("=") for pair in pairs)
            if DEBUG:
                print("CLIENT: %s" % header_line)
            while True:
                line = str(cl_file.readline(),'utf8').strip()
                if DEBUG:
                    print("CLIENT: %s" % line)
                if not line or line == b'\r\n':
                    break
            if header_line.startswith("GET"):
                if DEBUG:
                    print("RESPONDING TO GET")
                if req_file == "/":
                    if DEBUG:
                        print("FINALIZING AND SENDING DOCUMENT")
                    #finalize and send the document
                    header_bytes, doc_bytes = finalize_document()
                    cl.send(header_bytes)
                    cl.send(bytes("\r\n",'utf8'))  #IMPORTANT must have a blank line here
                    cl.send(doc_bytes)
                else:
                    if DEBUG:
                        print("WARNING: don't have file: %s" % req_file)
            elif header_line.startswith("POST"):
                if DEBUG:
                    print("RESPONDING TO POST")
                if req_file == "/":
                    if DEBUG:
                        print("FINALIZING AND SENDING DOCUMENT")
                    #finalize and send the document
                    header_bytes, doc_bytes = finalize_document(comment = "POSTED %r" % params)
                    cl.send(header_bytes)
                    cl.send(bytes("\r\n",'utf8'))  #IMPORTANT must have a blank line here
                    cl.send(doc_bytes)
        finally:
            cl_file.close()
            cl.close()
finally:
    s.close()
