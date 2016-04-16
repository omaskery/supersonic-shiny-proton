
# a note on the assembly language:
#
# with the exception of PUSH, all instructions have no arguments and are translated into
# a series of pushes (referred to hereafter as the ARGPUSH RULE), for example:
#
# add 10 15
#
# will compile to:
#
# push 10
# push 15
# add! 2  # note the ! after the instruction inhibits the ARGPUSH rule
#
# the "extra" 2 put after the add tells add how many variables were pushed before it

# example of ls:

# send ls to the system (shell) subsystem, which pushes the result onto the stack
send ["sys", "ls"] # this send uses the argpush rule
# stack is now [..., ls result]
push ["."]
# stack is now [..., ls result, ["."]]
swap
# stack is now [..., ["."], ls result]]
append! 1
# stack is now [..., [".", ls result]], sendi will now send the top result
# sendi ignores the response (should it still block? :S how to handle response otherwise?)
# when you send to target "." this means "send to the invoker of this process", typically
# this is the player's "local machine"
sendi # this sendi does not use the argpush rule

# example of saving to filesystem:

push "this is some text to write to file I guess"

# send an open message to the filesystem subsystem, file handle will be on stack afterwards
send ["fs", "open", "file.bin"]
# push beginings of send arguments for a filesystem write, we need the file handle next
push ["fs", "write"]
# swap the list we just pushed, and the file handle that should be beneath it
swap
# use append to pop the file handle and add it to the list just below it
append! 1
# stack should now be [..., data, ["fs", "write", file handle]] so swap data up to top
swap
# stack should now be [..., ["fs", "write", file handle], data] so append data to list
append! 1
# stack should now be [..., ["fs", "write", file handle, data]] so send this on to fs
send

# example of arithmetic (usual stack machine affair):

# pop 2 top values, add them and push the result to the stack
add 10 15

# imagine the other operators yourself

# example of complex types:

dict "john" 42 # (taking advantage of the argpush rule)

# or
push {"john": 42}

# or
push {}		# push an empty dictionary onto the stack
push "john"	# push the literal "john"
push 42		# push the literal 42
put		# pops the key ("john") and value (42) pair off the stack and puts them into the dictionary left on top of the stack (popping the dictionary at the top)

# or
push {}
put "john" 42 # variation of previous but using the argpush rule

push "john"
lookup		# pops the key ("john") off the stack and looks it up in the dictionary on the top of the stack (pops the dictionary, too), pushes the result

# can also be written:
lookup "john"

# list examples:

push [1, 2, 3]

# or

push 1
push 2
push 3
list! 3

# or

list 1 2 3 # uses the argpush rule

# or

push []		# push an empty list onto the stack
push 1
push 2
push 3
append! 3	# appends 3 items from the stack to the list it assumes is 'under' them, also for giggles it will append them IN THE ORDER PUSHED

# or

push []
append 1 2 3

lookup 0	# pushes the 0th element from a list on top of the stack (popping the list first)

# can also be written
push 0
lookup

len		# pops whatever is on top of the stack (list, dict, string, ...?) and pushes it's length/number of elements/whatever makes sense

# example of network send:

# assume some script is on top of the stack (loaded from FS or received from elsewhere...)
swap ["1.2.3.4:22"]
append! 1
send			# pops the value from top of stack, identifies that target is a remote machine and sends popped values to that remote machine

# example of receiving from another process:

recv

