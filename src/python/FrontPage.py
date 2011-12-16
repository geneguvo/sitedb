from RESTServer import RESTFrontPage
import os, re

class FrontPage(RESTFrontPage):
  """SiteDB front page.

  SiteDB V2 provides only one web page, the front page. The page just
  loads the javascript user interface, complete with CSS and all JS
  code embedded into it. The only additional callouts needed are the
  image resources needed for YUI and other site graphics.

  The javascript code performs all the app functionality via the REST
  interface defined by `Data` class. Mostly it just does bulk load of
  the various details, and organises it into a nice user interface,
  and where necessary and appropriate, offers an interface to edit the
  information. Virtually all interactive functionality is done on the
  client side, including things like searching.

  User navigation state is stored in the fragment part of the URL, e.g.
  <https://cmsweb.cern.ch/sitedb/prod/sites/T1_CH_CERN>."""

  def __init__(self, app, config, mount):
    """Initialise the main server."""
    CONTENT = os.path.abspath(__file__).rsplit('/', 5)[0]
    X = (__file__.find("/xlib/") >= 0 and "x") or ""
    roots = \
    {
      "sitedb":
      {
        "root": "%s/%sdata/" % (CONTENT, X),
        "rx": re.compile(r"^[a-z]+/[-a-z0-9]+\.(?:css|js|png|gif|html)$")
      },

      "yui":
      {
        "root": "%s/build/" % os.environ["YUI3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9/]+\.(?:css|js|png|gif)$")
      },

      "d3":
      {
        "root": "%s/data/" % os.environ["D3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9]+(?:\.min)?\.(?:css|js)$")
      }
    }

    frontpage = "sitedb/templates/sitedb.html"
    if os.path.exists("%s/templates/sitedb-min.html" % roots["sitedb"]["root"]):
      frontpage = "sitedb/templates/sitedb-min.html"

    RESTFrontPage.__init__(self, app, config, mount, frontpage, roots,
                           instances = lambda: app.views["data"]._db)
