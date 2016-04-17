
# this series of tests is for flow control

	sendi [".", "this is a test"]

	push 10

label start

	push 1
	sub

	dup -1
	zero?
	jn start

	pop 1

