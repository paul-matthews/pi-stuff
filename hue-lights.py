from datetime import datetime
from time import strptime,mktime
from operator import methodcaller
import json
import os.path
import requests

CACHE = {}

def get_cached(key, constructor):
	if not key in CACHE:
		CACHE[key] = constructor()
	return CACHE[key]

def get_hue():
	def do_get_hue():
		return Hue("./config.js")
	return get_cached("hue", do_get_hue)

class Light(object):
	def __init__(self, data={}, id=None):
		self.data = data
		self.id = id

	def __str__(self):
		data = self.data.copy()
		data['on'] = self.is_on(as_string=True)
		return "[name: %(name)s][on: %(on)s]" % data

	def is_on(self, as_string=False):	
		if as_string:
			return 'yes' if self.data['state']['on'] else 'no'
		return self.data['state']['on']

	@staticmethod
	def GET_ALL():
		def do_get_lights():
			raw = get_hue().get("lights")
			return dict((k, Light(v, k)) for (k, v) in raw.iteritems())
		return get_cached("lights", do_get_lights)

class Group(object):
	def __init__(self, data={}, id=None):
		self.data = data
		self.id = id
		self.lights = {}

	def __str__(self):
		return "[name: %(name)s]" % self.data

	def get_lights(self):
		if not self.lights:
			lights = Light.GET_ALL()
			self.lights = dict((l, lights[l]) for l in self.data['lights'])
		return self.lights

	@staticmethod
	def GET_ALL():
		def do_get_groups():
			raw = get_hue().get("groups")
			return dict((k, Group(v)) for (k, v) in raw.iteritems())
		return get_cached("groups", do_get_groups)

class Scene(object):
	URL_GET = "scenes"
	URL_SCENE = "scenes/%s"
	URL_ACTIVATE = "groups/0/action"

	def __init__(self, data={}, s_id=None):
		self.data = data
		self.id = s_id
		self.lights = {}

	def __str__(self):
		return "[name: %(name)s][last: %(lastupdated)s]" % self.data

	def activate(self):
		return get_hue().put(self.URL_ACTIVATE, {'scene': self.id})

	def delete(self):
		if not self.id:
			raise ValueError("Id not set")
		return get_hue().delete(self.URL_SCENE % self.id)

	def get_lights(self):
		if not self.lights:
			lights = Light.GET_ALL()
			self.lights = dict((l, lights[l]) for l in self.data['lights'])
		return self.lights

	def get_lastupdated(self):
		if not self.data['lastupdated']:
			return 0
		last = strptime(self.data['lastupdated'], "%Y-%m-%dT%H:%M:%S")
		return mktime(last)

	def is_on(self):
		for l in self.get_lights().values():
			if not l.is_on():
				return False
		return True

	@staticmethod
	def GET_ALL():
		def do_get_scenes():
			raw = get_hue().get(Scene.URL_GET)
			return dict((k, Scene(v, k)) for (k, v) in raw.iteritems())
		return get_cached("scenes", do_get_scenes)

	@staticmethod
	def GET_BY(name=None, on=None, before=None, after=None):
		scenes = Scene.GET_ALL().values()
		if name:
			scenes = [x for x in scenes if name in x.data['name']]

		if on is not None:
			scenes = [x for x in scenes if x.is_on()]

		if before is not None:
			scenes = [x for x in scenes if x.get_lastupdated() < before]

		if after is not None:
			scenes = [x for x in scenes if x.get_lastupdated() > before]

		return scenes

	@staticmethod
	def GET(id):
		scenes = Scene.GET_ALL()
		return scenes[id]

	@staticmethod
	def SORT_BY_DATE(scenes):
		return sorted(scenes, key=methodcaller('get_lastupdated'))


class Hue(object):
	BASE="http://%(ip)s/api/%(user)s/"
	TRANSFORMS = [os.path.expanduser, os.path.expandvars, os.path.realpath]

	def __init__(self, config_path):
		self.config = self.__get_config(config_path)

		self.server = self.config['server']
		self.user = self.config['user']
		self.lights = {}

	def get(self, path):
		return requests.get(self.__base_path() + path).json()

	def put(self, path, data):
		return requests.put(self.__base_path() + path, data=json.dumps(data))

	def delete(self, path):
		return requests.delete(self.__base_path() + path)

	def __base_path(self):
		return self.BASE % {'ip': self.server, 'user': self.user}

	def __get_config(self, config_path):
		config = {}
		with open(self.__get_config_path(config_path), 'r') as f:
			config = json.loads(f.read())
		return config

	def __set_config(self, config_path, config):
		with open(self.__get_config_path(config_path), 'w') as f:
			f.write(json.dumps(config, sort_keys=True, indent=4,
				separators=(',', ': ')))

	def __get_config_path(self, config_path):
		realpath = config_path
		for t in self.TRANSFORMS:
			realpath = t(realpath)
		return realpath

		

def print_all(obj, prefix=""):
	def print_lights(obj):
		if hasattr(v, 'get_lights'):
			for (i, l) in v.get_lights().iteritems():
				print " - %s) %s" % (i, l)

	def get_id(obj):
		if hasattr(obj, 'id') and obj.id:
			return " [id: %s]" % obj.id
		return ''

	if type(obj) == type({}):
		for (k, v) in obj.iteritems():
				print "%s) %s" % (k, v)
				print_lights(v)
	if type(obj) == type([]):
		for v in obj:
			print "-%s %s" % (get_id(v), v)
			print_lights(v)

			

if __name__ == "__main__":
	scenes = Scene.GET_BY(on=True)
	scenes = Scene.SORT_BY_DATE(scenes)
	# scenes = Scene.GET_BY(before=mktime(strptime("2016-02-01", "%Y-%m-%d")))
	print_all(scenes)
	# for s in scenes:
		# print "Deleteing: " + s.id
		# print s.delete().json()

	#print scenes["98fa71508-on-0"].activate().json()
	# print scenes["c02d0bf44-on-0"].activate().json()