# steamlabsSIS


teachable0: the main things to note about my teachable.py's is that I changed gpio 15 to 16 to save pwm space (meaning the yellow LED pin on Teachable Machine gets switched from PWM3 to GPIO73) and 33 to 37 (meaning the red LED pin from teachable gets switched from PWM2 to GPIO77). This version was actively being worked on so I'm leaving a stabler version that I forked directly from the google repository up in case anything goes horribly wrong. I do know I hadn't finished changing the button/LED pins to accommodate for only 3 of them being used?

servo: this is what i had for continuous servos. if you make them move any slower than this it doesn't work

switcher: hasn't been tested yet but uses the subprocess library which is better suited to this functionality than threading! if there are bugs they should be wranglable
