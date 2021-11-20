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

def str_to_pos(string):
	return np.array([float(coord) for coord in string.split()[:2]])

def apply_transformation(element, pos):
	if element.get("matrix") is not None:
		transformation = [float(coord) for coord in element["matrix"].split()]
		matrix = np.array(transformation[:4]).reshape(2, 2)
		shift = np.array(transformation[4:])
		pos = matrix@pos + shift
	return np.array(pos)*2

def ipe_to_json(filename, max_y):
	orb_list = []
	goals = []
	vectors = dict()  # start pos to direction

	soup = BeautifulSoup(open(filename, 'r').read(), features="html.parser")
	page = soup.find('page')
	paths = page.findAll('path', attrs={'stroke' : 'black'})
	for path in paths:
		coords = path.get_text().strip().split('\n')
		if path.get('arrow') == "normal/normal" and len(coords) == 2:
			origin = apply_transformation(path, str_to_pos(coords[0]))
			destination = apply_transformation(path, str_to_pos(coords[1]))
			direction = destination - origin
			vectors[tuple(origin)] = direction
		elif len(coords) == 5 and coords[4] == 'h':
			# TODO: Add some sanity checking
			pts = np.array([apply_transformation(path, str_to_pos(pos)) for pos in coords[:4]])
			rect = [
				np.min(pts[:,0]),
				max_y - min(max_y, np.max(pts[:,1])),
				np.max(pts[:,0]) - np.min(pts[:,0]),
				min(max_y, np.max(pts[:,1])) - np.min(pts[:,1]),
			]
			goals.append(rect)

	nodes = page.findAll('use', attrs={'name' : re.compile(r'^mark/.*')})
	for node in nodes:
		pos = str_to_pos(node["pos"])
		pos = apply_transformation(node, pos)
		vec = vectors.get(tuple(pos), np.array([0.0, 0.0]))
		vec *= 0.5
		vec[1] = -vec[1]
		pos[1] = max_y - pos[1]
		orb = {
			"pos" : pos,
			"charge" : charges[node["stroke"]], 
			"mass" : sizes[node["size"]],
			"velocity" : vec,
		}
		orb.update(props[node["name"]])
		orb_list.append(orb)

	return {
		'orbs': orb_list,
		'goals': goals,
	}
