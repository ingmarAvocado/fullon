"""
"""
import arrow


class reg(object):
    def __init__(self, cursor, row):
        try:
            for (attr, val) in zip((d[0] for d in cursor.description), row):
                setattr(self, attr, val)
        except:
            #print("except reg... something going on")
            return None


class ohlcv(object):

	def __init__(self, t1=False, t2=False):

		if t1:
			now = arrow.get().int_timestamp
			ts = arrow.get(t1.ts).int_timestamp 
			self.ts = arrow.get(ts).to('utc').naive
			self.epoch = arrow.get(t1.ts).int_timestamp
			self.open = t1.open
			self.high = t1.high
			self.low = t1.low
			self.close = t1.close
			self.vol = t1.vol

		elif t2 and t2[3] != None:
			now = arrow.get().int_timestamp
			self.ts = t2[0]
			self.epoch = arrow.get(self.ts).int_timestamp
			self.open = t2[1]
			self.high = t2[2]
			self.low = t2[3]
			self.close = t2[4]
			self.vol = t2[5]

		else:
			self.epoch = 0

		return None

