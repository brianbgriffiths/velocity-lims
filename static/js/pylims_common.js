function isodate() {
	const now = new Date();
	return isoDate = now.toISOString().split('T')[0];
}