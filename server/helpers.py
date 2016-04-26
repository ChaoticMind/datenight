from server import publishers


def clean_publishers():
	# index by nick instead of request.sid (which is private info)
	return {v['nick']: v for v in publishers.values()}
