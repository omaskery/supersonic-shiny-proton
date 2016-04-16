
# note on this assembly language:
#
# all instructions except PUSH can apply the "argpush" rule. this rule takes all
# parameters and turns them into pushes instead, followed by pushing the number of values
#
# add 10 15
#
# after applying the argpush rule becomes:
#
# push 10
# push 15
# push 2
# add

# example of ls:

# send ls to the system (shell) subsystem, which pushes the result onto the stack
send ["sys", "ls"] # this send uses the argpush rule
# stack is now [..., ls result, "sys"]
pop 1
# stack is now [..., ls result]
push ["."]
# stack is now [..., ls result, ["."]]
swap
# stack is now [..., ["."], ls result]
append 1
# stack is now [..., [".", ls result]], sendi will now send the top result
# sendi ignores the response (should it still block? :S how to handle response otherwise?)
# when you send to target "." this means "send to the invoker of this process", typically
# this is the player's "local machine"
sendi # this send has no arguments so it will pop a list to send

# example of saving to filesystem:

push "this is some text to write to file I guess"

# send an open message to the filesystem subsystem, file handle will be on stack afterwards
send ["fs", "open", "file.bin"]
# drop the sender
pop 1
# push beginings of send arguments for a filesystem write, we need the file handle next
push ["fs", "write"]
# swap the list we just pushed, and the file handle that should be beneath it
swap
# use append to pop the file handle and add it to the list just below it
push 1
append
# stack should now be [..., data, ["fs", "write", file handle]] so swap data up to top
swap
# stack should now be [..., ["fs", "write", file handle], data] so append data to list
push 1
append
# stack should now be [..., ["fs", "write", file handle, data]] so send this on to fs
send
# drop the sender and return code from write
push 2
pop

# example of arithmetic (usual stack machine affair):

push 10
push 15
# pop 2 top values, add them and push the result to the stack
add
pop 1

# imagine the other operators yourself

# example of creating a dict on top of the stack:

push "john"
push 42
dict 1
pop 1

# or
push {"john": 42}
pop 1

# or
push {}		# push an empty dictionary onto the stack
dup -1		# this dup is so a ref to dictionary remains after PUT
push "john"	# push the literal "john"
push 42		# push the literal 42
push 1
put		# pops the key ("john") and value (42) pair off the stack and puts them into the dictionary left on top of the stack (popping the dictionary at the top)

# looking up a value in a dict:

dup -1
lookup "john"		# pops the key ("john") off the stack and looks it up in the dictionary on the top of the stack (pops the dictionary, too), pushes the result
pop 1

# can also be written:
push "john"
lookup
pop 1

# list examples:

push [1, 2, 3]
pop 1

# or

push 1
push 2
push 3
push 3
list
pop 1

# or

push []		# push an empty list onto the stack
push 1
push 2
push 3
push 3
append # appends 3 items from the stack to the list it assumes is 'under' them, also for giggles it will append them IN THE ORDER PUSHED
pop 1

# or 

push []		# push an empty list onto the stack
push 1
push 2
push 3
append 3	# appends 3 items from the stack to the list it assumes is 'under' them, also for giggles it will append them IN THE ORDER PUSHED

# indexing into a list can be done as follows:

dup -1
lookup 0	# pushes the 0th element from a list on top of the stack (popping the list first)
pop 1

dup -1
# can also be written
push 1
lookup
pop 1

len		# pops whatever is on top of the stack (list, dict, string, ...?) and pushes it's length/number of elements/whatever makes sense
pop 1

# example of network send:

# some data to send
push ["stand", "in", "for", "some", "bytecode", "here"]
# some target destination
push ["1.2.3.4:22"]
swap
push 1
append
send			# pops the value from top of stack, identifies that target is a remote machine and sends popped values to that remote machine

# example of receiving from another process:

recv

