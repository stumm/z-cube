#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext import db
from django.utils import simplejson
import pprint
from xml.etree import ElementTree
import StringIO
import threading, os, sys
from google.appengine.api import users
from google.appengine.ext.webapp import template

# decorators
def loginRequired(func):
  def wrapper(self, *args, **kw):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
    else:
      func(self, *args, **kw)
  return wrapper
 
# models
class Device(db.Model):
    pw        = db.StringProperty(required=True)
    unique_id = db.StringProperty(required=True)
    last_url  = db.LinkProperty()
    last_login= db.DateTimeProperty()
    
    isactive  = db.BooleanProperty(default=True)
    name      = db.StringProperty(required=True)

    @property
    def auth_users(self):
        return db.GqlQuery("SELECT * FROM DeviceUsers WHERE device = :1", self.key())
        
class SimpleState(db.Model):
    color     = db.StringProperty(required=True)
    device    = db.ReferenceProperty(Device,required=True)
    isactive  = db.BooleanProperty(default=True)

class SiteUser(db.Model):
    login_user      = db.UserProperty()
    created         = db.DateTimeProperty(auto_now_add=True)
    site_nickname   = db.StringProperty()

    @property
    def auth_devices(self):
        return db.GqlQuery("SELECT * FROM DeviceUsers WHERE user = :1", self.key())
                
class DeviceUsers(db.Model):
    device    = db.ReferenceProperty(Device,collection_name="users")
    user      = db.ReferenceProperty(SiteUser,collection_name="devices")

class SetupDevice(webapp.RequestHandler):
    @loginRequired
    def get(self):
        ## here the user will set up their device
        ## they need to associate a password with a device ID
        pass

class SetupDevice(webapp.RequestHandler):

    def post(self):
        ## here the device will log in with it's password and ID and get the approppriate thing to do.
        pass       
 
class NewSiteUser(webapp.RequestHandler):
    @loginRequired
    def get(self):
        user = users.GetCurrentUser()
        result = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user = :1", user).get()
        if result:
            siteMsg = "<h2>Already Registered</h2><p>You are registered with the site, %s.</p>" % (result.site_nickname)
            deleteLink = """<a href="javascript:document.deleteForm.submit();">delete</a>"""
            deleteForm = """
            <form name="deleteForm" action="/newsiteuser" method="POST">
            <input type="submit" name="dodelete" value="Delete" />
            </form>"""
            siteMsg += "<p><a href='%s'>Return to Main Page</a> or %s yourself</p>%s" % ("/",deleteLink,deleteForm)
        else:
            ## create a new user
            siteMsg = """<h2>Register to Group-Think</h2<p>Enter your requested site nickname (eg. Bunny or Smelly Cat):</p>
            <form name="myform" action="/newsiteuser" method="POST">
            <div align="center"><br>
            <input type="text" name="site_nickname" />
            <input type="submit" name="theSubmitButton" value="Submit" />
            </div>
            </form>"""

        template_file_name = 'templates/newsiteuser.html'
        template_values = {'siteMsg': siteMsg }
        path = os.path.join(os.path.dirname(__file__), template_file_name)
        self.response.out.write(template.render(path, template_values))

    def post(self):
        #self.response.headers['Content-Type'] = 'text/html'
        siteMsg = """<h1>Z<sup>cube</sup></h1>"""

        user = users.GetCurrentUser()
        tmp = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user  = :1", user).get()
        if tmp:
            if self.request.get("dodelete") == 'Delete':
                siteMsg += "Deleted %s from Site Users" % tmp.login_user.nickname()
                tmp.delete()

        else:
            if self.request.get("site_nickname"):
                ## wanted to create a new user
                SiteUser(login_user=user,site_nickname=self.request.get("site_nickname")).put()
                siteMsg += """<h2>Created a new Site User.</h2> Welcome, %s<p><hr>""" % self.request.get("site_nickname")

        siteMsg += """<a href='%s'>Return to Main Page</a>""" % "/"

        template_file_name = 'templates/newsiteuser.html'
        template_values = {'siteMsg': siteMsg }
        path = os.path.join(os.path.dirname(__file__), template_file_name)
        self.response.out.write(template.render(path, template_values))

class ShowDevices(webapp.RequestHandler):
    @loginRequired
    def get(self):
        user = users.GetCurrentUser()
        siteuser = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user  = :1", user).get()
        if not siteuser:
            ## this dude aint logged in
            self.redirect("/newsiteuser")
    # FIXME

def check_color_good(c):
    if not isinstance(c,str):
        return False
    
    if len(c) != 6:
        return False
    
    for l in c:
        if l not in "012345679abcdef":
            return False
    
    return True
    
class GetColor(webapp.RequestHandler):
    #@loginRequired
    # http://localhost:8080/getcolor?uid=00:00:00:00:00:01&pwd=a
    def get(self):
        #self.response.out.write("hi!")
        #return
        #self.response.headers['Content-Type'] = 'application/json'
        uid=self.request.get("uid")
        pw=self.request.get("pwd")
        if (uid is None) or (pw is None):
            self.response.out.write("""{ "type": "err", "c": "ff0000", "cmt": "req err %s %s"}""" % (uid,pw))
            return
            
        dev = db.GqlQuery("SELECT * FROM Device WHERE unique_id  = :1 and pw = :2" , uid, pw).get()
        if dev is None:
            self.response.out.write("""{ "type": "err", "c": "ff0000", "cmt": "no dev %s %s"}""" % (uid,pw))
            return
        
        if not dev.isactive:
            self.response.out.write("""{ "type": "err", "c": "ff0000", "cmt": "dev not active %s %s"}""" % (uid,pw))
            return
        
        # TODO probably want to have all the different States types searched
        ss = db.GqlQuery("SELECT * FROM SimpleState WHERE device  = :1 and isactive = :2" , dev, True).get() 
        if ss is None:
            self.response.out.write("""{ "type": "err", "c": "ff0000", "cmt": "no active color state %s %s"}""" % (uid,pw))
            return
            
        self.response.out.write("""{ "type": "s", "c": "%s", "cmt": "ok"}""" % (ss.color))
        return
                  
class SetColor(webapp.RequestHandler):
    @loginRequired
    
    def post(self):
        user = users.GetCurrentUser()
        siteuser = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user  = :1", user).get()
        if not siteuser:
            ## this dude aint logged in
            self.redirect("/newsiteuser")
            
        uid = self.request.get("uid")
        dev = db.GqlQuery("SELECT * FROM Device WHERE unique_id  = :1", uid).get()
        if dev is None:
            template_file_name = 'templates/main.html'
            template_values = {'main': "There is no device with those credential setup. Perhaps you should <a href='/add_device'>add a new device</a>. " }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        if self.request.get("siteuser") != str(siteuser.key()):
            template_file_name = 'templates/main.html'
            template_values = {'main': "You are not authorized to edit that device. Go back on your browser and fix this." }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        du = db.GqlQuery("SELECT * FROM DeviceUsers WHERE device  = :1 and user = :2" , dev, siteuser).get()
        if du is None:
            template_file_name = 'templates/main.html'
            template_values = {'main': "You are not authorized to edit that device. Go back on your browser and fix this." }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        col = self.request.get("colorfield1")
        try:
            col = col.lower().encode()
        except:
            pass
        if not check_color_good(col):
            template_file_name = 'templates/main.html'
            template_values = {'main': "Invalid color request %s." % col }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        ss = db.GqlQuery("SELECT * FROM SimpleState WHERE device  = :1", dev).get()
        if ss is None:
            oldcol = "ffffff"
            SimpleState(color=col,device=dev).put()
        else:
            oldcol = ss.color
            ss.color = col
            ss.put()
        
        template_file_name = 'templates/main.html'
        template_values = {'main': """Set color request for your device (%s, %s) to <font color='#%s'>%s</font>. 
        Previous color was <font color='#%s'>%s</font>""" % \
            (dev.name,dev.unique_id,col,col,oldcol,oldcol) }
        path = os.path.join(os.path.dirname(__file__), template_file_name)
        self.response.out.write(template.render(path, template_values))
        return
            
class AddDevice(webapp.RequestHandler):
    @loginRequired
    
    def get(self):
        
        user = users.GetCurrentUser()
        siteuser = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user  = :1", user).get()
        if not siteuser:
            ## this dude aint logged in
            self.redirect("/newsiteuser")
        
        template_file_name = 'templates/newdevice.html'
        template_values = {'siteuser': siteuser }
        path = os.path.join(os.path.dirname(__file__), template_file_name)
        self.response.out.write(template.render(path, template_values))

# http://www.google.com/finance/info?client=ig&q=GOOG
class ConfirmDevice(webapp.RequestHandler):
    @loginRequired
    def post(self):
        user = users.GetCurrentUser()
        siteuser = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user  = :1", user).get()
        if not siteuser:
            ## this dude aint logged in
            self.redirect("/newsiteuser")
        
           
        uid = self.request.get("pn")
        if not uid:
            # no device ID given, barf
            template_file_name = 'templates/main.html'
            template_values = {'main': "Unique ID malformed. Press back on your browser to fix this." }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        dev = db.GqlQuery("SELECT * FROM Device WHERE unique_id  = :1", uid).get()
        if dev is not None:
            ## ew. this device already exists
            template_file_name = 'templates/main.html'
            ss = """<div>Device exists already! If you made a mistake, correct the unique ID number by pressing back on your browser.</div>"""
            ss += "\n<div>Or, if your are the owner of the device, you can <a href='/editdevice?id=%s'>edit the device settings</a></div>" % str(uid)
            template_values = {'main': ss }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
        
        pw1 = self.request.get("pw1")
        pw2 = self.request.get("pw2")
        if pw1 != pw2:
            template_file_name = 'templates/main.html'
            template_values = {'main': "Passwords do not match. Press back on your browser to fix this." }
            path = os.path.join(os.path.dirname(__file__), template_file_name)
            self.response.out.write(template.render(path, template_values))
            return
                
        nm = self.request.get("nm")
        
        for d in siteuser.auth_devices:
            if d.device.name == nm:
                template_file_name = 'templates/main.html'
                ss = """<div>You already have a device named %s. Press back on your browser to change your device name</div>""" % nm
                template_values = {'main': ss }
                path = os.path.join(os.path.dirname(__file__), template_file_name)
                self.response.out.write(template.render(path, template_values))
                return
        
        dev = Device(pw=pw1,unique_id=uid,isactive=True,name=nm)
        dev.put()
        
        DeviceUsers(device=dev,user=siteuser).put()
        greeting = " Welcome, %s" % siteuser.site_nickname
        ## it truly is a new device, let's get it set up.
        mess = "<div class='mess'>You have sucessfully set up your Z<sup>cube</sup>! It is now called '%s'</div>" % nm
        template_file_name = 'templates/configdev.html'
        #'onload': 'class=" yui-skin-sam"',
        template_values = { 'mess': mess, 'name': nm, 'uid': uid, 'siteuser': siteuser.key(), 'nick': user.nickname(), 'greeting': greeting}
        
        path = os.path.join(os.path.dirname(__file__), template_file_name)
        self.response.out.write(template.render(path, template_values))
        return
        
class MainHandler(webapp.RequestHandler):

  def get(self):
      user = users.GetCurrentUser()
      login = users.CreateLoginURL(self.request.uri)
      logout = users.CreateLogoutURL(self.request.uri)
      if user:
          result = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user = :1", user).get()
          if result:
              greeting = " Welcome, %s" % result.site_nickname
          else:
              greeting = "(<a href='%s'>Click here to get started as a site user</a>)" % "/newsiteuser"

          nick = user.nickname()
          logout_url = users.create_logout_url(self.request.uri)
      else:
          self.redirect(users.create_login_url(self.request.uri))
          result = db.GqlQuery("SELECT * FROM SiteUser WHERE login_user = :1", user).get()
          self.response.out.write('%s' % repr(result))
          user = users.GetCurrentUser()
          nick = ""
          try:
              greeting = " Welcome, %s" % result.site_nickname
          except:
              greeting = ""
          logout_url = users.create_logout_url(self.request.uri)

      template_file_name = 'templates/main.html'
      
      template_values = {'main': "hi", 'greeting': greeting, 'nick': nick, 'logout_url': logout_url}
      path = os.path.join(os.path.dirname(__file__), template_file_name)
      self.response.out.write(template.render(path, template_values))
      
      #self.response.out.write('off')


def main():
    
    apps_binding = []
    apps_binding.append(('/', MainHandler))
    apps_binding.append(('/newsiteuser', NewSiteUser))
    apps_binding.append(('/add_device', AddDevice))
    apps_binding.append(('/confirm_device_setup', ConfirmDevice))
    apps_binding.append(('/setcolor',SetColor))
    apps_binding.append(('/getcolor',GetColor))
    apps_binding.append(('/mydevices',ShowDevices))
    
    application = webapp.WSGIApplication(apps_binding,
                                       debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
