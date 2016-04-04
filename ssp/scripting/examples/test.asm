
# example of ls:

push ["sys", "ls"]
send
push ["."]
send

# example of saving to filesystem:

# (assume data to write is top of the stack)

push ["fs", "open", "file.bin"]
send 		# pops 2 things from the stack and sends it to the "fs" subsystem (filesystem), the response (a filehandle) is pushed to the stack (or negative error #)

push ["fs", "write"]
swap
append 1
dup -1		# copies (SP - 1) item and pushes it to the stack (data to write, assumed to be on stack at beginning of example)
send		# invoke filesystem write

# example of arithmetic (usual stack machine affair):

push 10		# push a constant
push 15		# push another constant
add		# pop 2 top values, add them and push the result to the stack

# imagine the other operators yourself

# example of complex types:

push "john"
push 42
dict 1		# pops 1 PAIRS of values and treats them as key-value pairs, pushing a resultant dict

# or
push {"john": 42}

# or
push {}		# push an empty dictionary onto the stack
push "john"	# push the literal "john"
push 42		# push the literal 42
put		# pops the key ("john") and value (42) pair off the stack and puts them into the dictionary left on top of the stack (popping the dictionary at the top)

push "john"
lookup		# pops the key ("john") off the stack and looks it up in the dictionary on the top of the stack (pops the dictionary, too), pushes the result

push [1, 2, 3]

# or

push 1
push 2
push 3
list 3

# or

push []		# push an empty list onto the stack
push 1
push 2
push 3
append 3	# appends 3 items from the stack to the list it assumes is 'under' them, also for giggles it will append them IN THE ORDER PUSHED

lookup 0	# pushes the 0th element from a list on top of the stack (popping the list first)

len		# pops whatever is on top of the stack (list, dict, string, ...?) and pushes it's length/number of elements/whatever makes sense

# example of network send:

# assume some script is on top of the stack (loaded from FS or received from elsewhere...)
push ["1.2.3.4:22"]
swap
append 1
send			# pops the value from top of stack, identifies that target is a remote machine and sends popped values to that remote machine

# example of receiving from another process:

recv

