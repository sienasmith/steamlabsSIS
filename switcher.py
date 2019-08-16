import python-periphery
import shlex, subprocess #shlex is for splitting the command string and subprocess is like threading but chunkier and killable

switch = GPIO(8, "in")

lastwas = False #switch state change detection
classifier = subprocess.Popen(shlex.split("### CLASSIFIER COMMAND GOES HERE ###"), shell=True) #open the classifier
while True:
    if switch.read == True and lastwas == False: #if the switch state has changed to true
        classifier.kill() #end classifier
		teachable = subprocess.Popen(shlex.split("echo 'mendel' | sudo -S python3 ~/project-teachable/teachable.py"), shell=True) #runs this in shell
		lastwas = True
	elif switch.read == False and lastwas == True #if switch state has changed to false
		teachable.kill()
		classifer = subprocess.Popen(shlex.split("### CLASSIFIER COMMAND GOES HERE ###"), shell=True)
		lastwas = False