import time, socket
import mock_machine as machine

try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micrpython specific

DEBUG = False
DEBUG = True

PIN_NUMBERS = (0, 2, 4, 5, 12, 13, 14, 15)
SERVER_IP = '0.0.0.0'

PINS = OrderedDict((i,machine.Pin(i, machine.Pin.IN)) for i in PIN_NUMBERS)

#here are some mocked test settings
PINS[0].value = True  #sets pin "0" to high
PINS[5].value = True  #sets pin "5" to high


doc_template = """
<!DOCTYPE html>
<html>
    <head> <title>ESP8266 Pins</title>
    </head>
    <body> <h1>ESP8266 Pins</h1>
        <table border="1"> <tr><th>Pin</th><th>Value</th></tr>{table_content}</table>
        <div>{comment}</div>
    </body>
    <script>
        {javascript}
    </script>
</html>
"""

doc_template = doc_template.strip() #remove troublesome leading (and trailing) whitespace

javascript_template = """
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
            form.setAttribute('action', 'http://%s?btn_id='+btn_id);
            form.style.display = 'hidden';
            document.body.appendChild(form)
            form.submit();
          }
"""
javascript = javascript_template % SERVER_IP

javascript = javascript.strip()

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

def finalize_document(pins, comment = ""):
    #NOTE this content must be generated dynamically
    rows = [row_template.format(pin_id = str(pin),pin_value=pin.value()) for pn,pin in pins.items()]
    
    rows = ' '.join(rows) #empty line cause row to indent properly
            
    doc = doc_template.format(javascript = javascript,
                              table_content = rows,
                              comment = comment,
                              )
    doc_bytes = bytes(doc,'utf8')
    headers = headers_template.format(content_length = len(doc_bytes)) #now assign the content's length
    header_bytes = bytes(headers,'utf8')
    return (header_bytes, doc_bytes)


addr = socket.getaddrinfo(SERVER_IP, 80)[0][-1]

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
                items = req[1].split("&")
                for item in items:
                    item = item.split("=")
                    if len(item) == 1:
                        params[item[0]] = None
                    elif len(item) == 2:
                        params[item[0]] = item[1]
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
                    header_bytes, doc_bytes = finalize_document(pins = PINS)
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
                    #get the button id from the params and pull out the corresponding pin object
                    btn_id = params['btn_id']
                    pin_id = int(btn_id[3:])#pattern is "btn\d\d"
                    pin = PINS[pin_id]
                    pin.value = not pin.value()
                    #finalize and send the document
                    header_bytes, doc_bytes = finalize_document(pins = PINS, comment = "Toggled pin %d" % pin_id)
                    cl.send(header_bytes)
                    cl.send(bytes("\r\n",'utf8'))  #IMPORTANT must have a blank line here
                    cl.send(doc_bytes)
        finally:
            cl_file.close()
            cl.close()
finally:
    s.close()
