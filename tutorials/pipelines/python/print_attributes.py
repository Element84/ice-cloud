# The filters.programmable filter expects a function name in the
# module that has at least two arguments -- "ins" which
# are numpy arrays for each dimension, and the "outs" which
# the script can alter/set/adjust to have them updated for
# further processing.
def print_attributes(ins, outs):
    for key in ins.keys():
        print (key)
    # filters.programmable scripts need to
    # return True to tell the filter it was successful.
    return True