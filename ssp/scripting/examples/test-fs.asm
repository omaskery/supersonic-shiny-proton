
    # open a file handle
    send ["fs", "open", "w", "test.txt"]
    # copy the result pair onto the stack
    dup -1
    # extract the retcode
    lookup 1
    # see if it's zero (success)
    zero?
    # if not, jump to error handling
    jn error
    # otherwise extract file handle from result pair
    lookup 0

    # push start of write command to stack
    push ["fs", "write"]
    # duplicate file handle
    dup -2
    # append file handle to command
    append 1
    # push data onto stack
    push "this is some data"
    # append data to command
    append 1
    # send command
    send
    # duplicate retcode
    dup -1
    # check retcode for success (zero)
    zero?
    # if not, jump to error
    jn error
    # emit success
    sendi [".", "success! :D"]
    # go to end
    jmp end
    
label error
    push [".", "oops it broke:"]
    swap
    append 1
    sendi
    jmp end

label end
    nop
