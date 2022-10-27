def combine_comments(first, second):
    final_comment = first
    if second:
        if first:
            final_comment += '. ' + second
        else:
            final_comment = second
    return final_comment