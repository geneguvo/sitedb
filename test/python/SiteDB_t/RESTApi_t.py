from cherrypy.test import test, webtest, helper
from SiteDB.RESTServer import RESTApi, RESTEntity, restcall, rows
from SiteDB.RESTTest import setup_test_server, fake_authz_headers
from SiteDB.RESTValidation import validate_num
from SiteDB.RESTError import InvalidObject
from SiteDB.RESTFormat import RawFormat
from SiteDB.RESTTools import tools
from cherrypy import expose
import cjson

server = None
authz_key = None
gif_bytes = ('GIF89a\x01\x00\x01\x00\x82\x00\x01\x99"\x1e\x00\x00\x00\x00\x00'
             '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
             '\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x02\x03\x02\x08\t\x00;')

class Simple(RESTEntity):
  def validate(self, *args): pass

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return rows(['foo'])

class Multi(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    validate_num("lim", param, safe, bare=True,
		 optional=True, minval=0, maxval=10)

  def _generate(self, lim):
    for i in xrange(0, 10):
      if i == lim:
        raise InvalidObject("cut at %d" % i)
      yield ["row", i]

    if i == lim:
      raise InvalidObject("cut at %d" % i)

  @restcall
  @tools.expires(secs=300)
  def get(self, lim):
    if lim == 0:
      raise InvalidObject("cut at 0")

    return self._generate(lim)

class Image(RESTEntity):
  def validate(self, *args): pass

  @restcall(formats=[("image/gif", RawFormat())])
  @tools.expires(secs=300)
  def get(self):
    return gif_bytes

class Root(RESTApi):
  def __init__(self, app, config):
    RESTApi.__init__(self, app, config)
    self._add({ "simple": Simple(app, self, config),
	        "image":  Image(app, self, config),
	        "multi":  Multi(app, self, config) })

class Tester(helper.CPWebCase):
  def _test_accept_ok(self, fmt, page = "/test/simple", inbody = None):
    h = fake_authz_headers(authz_key.data) + [("Accept", fmt)]
    self.getPage(page, headers = h)
    self.assertStatus("200 OK")
    if fmt.find("*") >= 0:
      self.assertHeader("Content-Type")
    else:
      self.assertHeader("Content-Type", fmt)
    self.assertHeader("X-REST-Status", "100")
    self.assertHeader("X-REST-Time")
    self.assertNoHeader("X-Error-ID")
    self.assertNoHeader("X-Error-HTTP")
    self.assertNoHeader("X-Error-Info")
    self.assertNoHeader("X-Error-Detail")
    if inbody:
      self.assertInBody(inbody)

  def _test_accept_fail(self, fmt, page="/test/simple",
		        avail="application/json, application/xml"):
    h = fake_authz_headers(authz_key.data) + [("Accept", fmt)]
    self.getPage(page, headers = h)
    self.assertStatus("406 Not Acceptable")
    self.assertHeader("X-REST-Status", "201")
    self.assertHeader("X-REST-Time")
    self.assertHeader("X-Error-ID")
    self.assertHeader("X-Error-HTTP", "406")
    self.assertHeader("X-Error-Info", "Available types: %s" % avail)
    self.assertHeader("X-Error-Detail", "Not acceptable")
    self.assertInBody("Not acceptable")

  def test_accept_good_json(self):
    self._test_accept_ok("application/json", inbody="foo")

  def test_accept_good_xml(self):
    self._test_accept_ok("application/xml", inbody="foo")

  def test_accept_good_gif(self):
    self._test_accept_ok("image/gif", page="/test/image")
    self.assertBody(gif_bytes)

  def test_accept_good_gif2(self):
    self._test_accept_ok("image/*", page="/test/image")
    self.assertBody(gif_bytes)

  def test_accept_reject_octets(self):
    self._test_accept_fail("application/octet-stream")

  def test_accept_reject_xfoo(self):
    self._test_accept_fail("application/x-foo")

  def test_accept_reject_gif(self):
    self._test_accept_fail("image/gif")

  def test_accept_reject_gif2(self):
    self._test_accept_fail("image/png", page="/test/image", avail="image/gif")

  def test_accept_reject_png(self):
    self._test_accept_fail("image/png")

  def test_simple_json(self):
    h = fake_authz_headers(authz_key.data)
    h.append(("Accept", "application/json"))
    self.getPage("/test/simple", headers = h)
    self.assertStatus("200 OK")
    b = cjson.decode(self.body)
    assert isinstance(b, dict)
    assert "desc" not in b
    assert "result" in b
    assert isinstance(b["result"], list)
    assert len(b["result"]) == 1
    assert b["result"][0] == "foo"

  def test_multi_nothrow(self):
    h = fake_authz_headers(authz_key.data)
    h.append(("Accept", "application/json"))
    self.getPage("/test/multi", headers = h)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")
    b = cjson.decode(self.body)
    assert isinstance(b, dict)
    assert "desc" not in b
    assert "result" in b
    assert isinstance(b["result"], list)
    assert len(b["result"]) == 10
    for i in xrange(0, 10):
      assert isinstance(b["result"][i], list)
      assert b["result"][i][0] == "row"
      assert b["result"][i][1] == i

  def test_multi_throw0(self):
    h = fake_authz_headers(authz_key.data)
    h.append(("Accept", "application/json"))
    self.getPage("/test/multi?lim=0", headers = h)
    self.assertStatus(400)
    self.assertHeader("X-REST-Status", "306")
    self.assertHeader("X-Error-HTTP", "400")
    self.assertHeader("X-Error-Info", "cut at 0")
    self.assertHeader("X-Error-Detail", "Invalid object")
    self.assertHeader("X-Error-ID")

  def test_multi_throw5(self):
    h = fake_authz_headers(authz_key.data)
    h.append(("Accept", "application/json"))
    self.getPage("/test/multi?lim=5", headers = h)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")
    b = cjson.decode(self.body)
    assert isinstance(b, dict)
    assert "desc" not in b
    assert "result" in b
    assert isinstance(b["result"], list)
    assert len(b["result"]) == 5
    for i in xrange(0, 5):
      assert isinstance(b["result"][i], list)
      assert b["result"][i][0] == "row"
      assert b["result"][i][1] == i

  def test_multi_throw10(self):
    h = fake_authz_headers(authz_key.data)
    h.append(("Accept", "application/json"))
    self.getPage("/test/multi?lim=10", headers = h)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")
    b = cjson.decode(self.body)
    assert isinstance(b, dict)
    assert "desc" not in b
    assert "result" in b
    assert isinstance(b["result"], list)
    assert len(b["result"]) == 10
    for i in xrange(0, 10):
      assert isinstance(b["result"][i], list)
      assert b["result"][i][0] == "row"
      assert b["result"][i][1] == i

def setup_server():
  global server, authz_key
  srcfile = __file__.split("/")[-1].split(".py")[0]
  server, authz_key = setup_test_server(srcfile, "Root")
  #import cherrypy; cherrypy.config.update({"log.screen": True})

if __name__ == '__main__':
  setup_server()
  helper.testmain()