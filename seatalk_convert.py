#Copyright (C) 2020 by GeDaD <https://github.com/Thomas-GeDaD/openplotter-MCS>
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# any later version.
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.
#
# 2020-07-03 @MatsA Added function for inverting signal and using RPi internal pull up/down
# 2020-08-18 Updated according to Thomas-GeDaD commits => reduce cpu consumption & Fix first character if 0x00 / string =00
# 2020-11-05 marcobergman changed code to export NMEA0183 sentences nstead 
#

import pigpio, time, socket, signal, sys, os

port=4041				# Define UDP port for sending
ip= '127.0.0.1' # Define ip default localhost 127.0.0.1
gpio = 2  			# Define gpio where the SeaTalk1 (yellow wire) is sensed
invert = 1      # Define if input signal shall be inverted 0 => not inverted, 1 => Inverted 
pud = 2         # define if using internal RPi pull up/down 0 => No, 1= Pull down, 2=Pull up
talker = "RM" 	# Talker on the NMEA bus

def initialize_pigpiod():  
	print ("Shutting down old gpiod")
	os.system("pkill pigpiod")
	print ("...waiting for it to shut down")
	time.sleep(1)
	print ("Starting new gpiod")
	os.system("pigpiod")
	print ("...waiting for new gpiod to start up")
	time.sleep(1)
	print ("Ready")

initialize_pigpiod()

stw = 555
hdg = 555
last_datagram = 555

def getByte(hexstring):
	if len(hexstring) == 1:
		hexstring = "0" + hexstring;
	try:
		return ord(bytes.fromhex(hexstring))
	except Exception as e:
		print (str(e))
		return 0


def nmeaChecksum(s): # str -> two hex digits in str
	chkSum = 0
	subStr = s[1:len(s)]

	for e in range(len(subStr)):
		chkSum ^= ord((subStr[e]))

	hexstr = str(hex(chkSum))[2:4]
	if len(hexstr) == 2:
		return hexstr
	else:
		return '0'+hexstr

def nmea_sentence(sentence)
	return "$" + talker + sentence + "*" + nmeaChecksum(sentence) + "\r\n"


def formatHDM(byte1, byte2):
	hdg = ((byte1 // 16) & ord('\x03')) * 90 + (byte2 & ord('\x3f')) * 2 + ((byte1 // 16 // 8) & ord('\x01'))
	if (hdg == None): 
		return None
	hdg = '{:3.1f}'.format(hdg)

	sentence = "HDM,%s,M" % (hdg)
	
	return nmea_sentence(sentence)


def formatVHW(byte2, byte3):
	stw = (byte3*256 + byte2 + 0.0)/10
	if (hdg == None) or (stw == None) or (hdg < 0.1):
		return None
	hdm = ''
	hdt = ''
	stwn = '{:3.1f}'.format(stw)
	stwk = ''

	sentence = "VHW,%s,T,%s,M,%s,N,%s,K" % (hdt, hdm, stwn, stwk)
	
	return nmea_sentence(sentence)

def formatVLW(byte1, byte2, byte3, byte4, byte5, byte6):
	total = (byte2 + byte3*256 + (byte1 // 16)*4096) / 10
	trip = (byte4 + byte5*256 + (byte6 & ord('\x0f'))*65536) / 100

	if (trip == None) or (total == None):
		return None
	total = '{:3.1f}'.format(total)
	trip = '{:3.1f}'.format(trip)

	sentence = "VLW,%s,N,%s,N" % (total, trip)
	
	return nmea_sentence(sentence)


def formatMTW(byte2):
	temp = (byte2 - 100.0)/10
	if (mtw == None): 
		return None
	tmp = '{:3.1f}'.format(mtw)

	sentence = "MTW,%s,C" % (tmp)
	
	return nmea_sentence(sentence)

def translate_st_to_nmea (data):
	global stw
	global hdg
	global last_datagram

	if not data:
		return 
	bytes = data.split(",")
	print ("{}".format(str(bytes)))

	datagram = getByte(bytes[0])
	if datagram == last_datagram:
		print ("datagram = last datagram", bytes[0])
		return
	last_datagram = datagram

	try:
		if datagram == ord('\x20'):
			byte2 = getByte(bytes[2])
			byte3 = getByte(bytes[3])
			return formatVHW(byte2, byte3)
		if datagram == ord('\x25'):
			byte1 = getByte(bytes[1])
			byte2 = getByte(bytes[2])
			byte3 = getByte(bytes[3])
			byte4 = getByte(bytes[4])
			byte5 = getByte(bytes[5])
			byte6 = getByte(bytes[6])
			return formatVLW(byte1, byte2, byte3, byte4, byte5, byte6)
		if datagram == ord('\x27'):
			byte2 = getByte(bytes[2])
			return formatMTW(byte2)
		elif datagram == ord('\x89'): # Coming from ST50 Compass
			byte1 = getByte(bytes[1])
			byte2 = getByte(bytes[2])
			return formatHDM(byte1, byte2)
		elif datagram == ord('\x9c'): # Coming from ST2000
			u2 = getByte(bytes[1])
			vw = getByte(bytes[2])
			hdg2 = ((u2 // 16) & ord('\x03')) * 90 + (vw & ord('\x3f')) * 2 + ((u2 // 16 // 8) & ord('\x01'))
			#return formatHDM(hdg2)
			return None
		elif datagram == ord('\x84'): #Coming from ST2000
			return None
		elif datagram == ord('\x23'): #Coming from Raymarine Speed
			return None
		elif datagram == ord('\x26'): #Coming from Raymarine Speed
			return None
		elif datagram == ord('\x60'): #Coming from Raymarine ST50 Compass
			return None
		else:
			print ('Unknown datagram ' + bytes[0])
	except Exception as e:
		print ("*** Could not parse " + str(bytes) + ": " + str(e))



if __name__ == '__main__':

	st1read =pigpio.pi()

	try:
		st1read.bb_serial_read_close(gpio) 	# close if already run
	except:
		pass
	
	st1read.bb_serial_read_open(gpio, 4800,9)	# Read from chosen GPIO with 4800 Baudrate and 9 bit
	#st1read.bb_serial_invert(gpio, invert)		# Invert data
	st1read.set_pull_up_down(gpio, pud)		# Set pull up/down
	
	data=""
    
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	try:
		while True:
			out=(st1read.bb_serial_read(gpio))
			out0=out[0]
			if out0>0:
				out_data=out[1]
				x=0
				while x < out0:
					if out_data[x+1] ==0:
						string1=str(hex(out_data[x]))[2:]
						data= data+string1+ ","
					else:
						data=data[0:-1] # cut off trailing comma
						nmea_sentence = translate_st_to_nmea (data)
						if nmea_sentence:
							sys.stdout.write (nmea_sentence)
							sock.sendto(nmea_sentence.encode('utf-8'), (ip, port))
						else:
							print ("ignored")

						string2=str(hex(out_data[x]))[2:]
						if len(string2)==1:
							string2="0"+string2
						data=string2 + ","

					x+=2
			time.sleep(0.01)
				
	except KeyboardInterrupt:
		st1read.bb_serial_read_close(gpio)
		print ("exit")

