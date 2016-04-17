
# this series of tests is for flow control

	sendi [".", "this is a test"]

	push 10

label start

	push [".", "iteration:"]
	dup -2
	append 1
	sendi

	push 1
	sub

	dup -1
	zero?
	push start
	jn

	pop 1

