from bs4 import BeautifulSoup
import json
import re
import numpy as np

sizes = {
	"large" : 2, 
	"normal" : 1, 
	"small" : 0.5, 
	"tiny" : 0.25, 
}

charges = {
	"darkblue" : -2,
	"blue" : -1,
	"lightblue" : -0.5,
	"pink" : 0.5,
	"red" : 1,
	"darkred" : 2,
}

props = {
	"mark/box(sx)":    {"is_fixed": False, "is_player": True},
	"mark/square(sx)": {"is_fixed": True,  "is_player": True},
	"mark/circle(sx)": {"is_fixed": False, "is_player": False},
	"mark/disk(sx)":   {"is_fixed": True,  "is_player": False},
}

def ipe_to_json(filename, max_y):
	soup = BeautifulSoup(open(filename, 'r').read(), features="html.parser")
	page = soup.find('page')
	nodes = page.findAll('use', attrs={'name' : re.compile(r'^mark/.*')})
	orb_list = []
	for node in nodes:
		pos = np.array([float(coord) for coord in node["pos"].split()])
		if node.get("matrix") is not None:
			transformation = [float(coord) for coord in node["matrix"].split()]
			matrix = np.array(transformation[:4]).reshape(2, 2)
			shift = np.array(transformation[4:])
			pos = matrix@pos + shift
		pos *= 2
		pos[1] = max_y - pos[1]
		orb = dict({
			"pos" : pos,
			"charge" : charges[node["stroke"]], 
			"mass" : sizes[node["size"]], 
		}, **props[node["name"]])
		orb_list.append(orb)
	return orb_list
