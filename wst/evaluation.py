# -*- coding: utf8 -*-
#
# Survey evaluation module.
#

import os
import sys
import json

import pylab


def all_datasets(path, predicate=None):
    if predicate is None:
        predicate = lambda x: True
    for fn in os.listdir(path):
        fn = os.path.join(path, fn)
        try:
            survey = json.load(open(fn, "rb"))
        except IOError, ex:
            print ex
            continue
        if not predicate(survey):
            continue
        yield survey["questions"]


def collect_questions(path, predicate=None):
    questions, answers = [], []
    for survey in all_datasets(path, predicate):
        while len(questions) < len(survey):
            questions.append(None)
            answers.append([])
        for idx, q in enumerate(survey):
            answers[idx].append(q["answer"])
            if not questions[idx]:
                q.pop("answer")
                questions[idx] = q
    return questions, answers


def evaluate_question(question, answers):
    question_type = question["type"]
    if question_type == "yes-no":
        choices = question["choices"]
        subquestions = question["subquestions"]
    else:
        choices = []
        subquestions = []
    comments = []
    sub_totals = [ [0.0 for j in choices] for i in subquestions ]
    for answer in answers:
        if answer and answer.get("comment"):
            comments.append(answer["comment"])
        if question_type == "yes-no":
            for i_sub_q, sub_a in enumerate(answer["answers"]):
                norm = 1.0 / (sum(sub_a) or 1.0)
                norm_sub_a = [ a * norm for a in sub_a ] 
                sub_totals[i_sub_q] = map(sum, zip(
                    sub_totals[i_sub_q], norm_sub_a
                ))
    #for i, sub_total in enumerate(sub_totals):
    #    print subquestions[i]
    #    print zip(choices, sub_total)
    #print comments
    return [ zip(choices, sub_total) for sub_total in sub_totals ], comments


def plot_question(fname, question_text, data):
    pylab.figure().clear()
    pylab.title(question_text)
    if True or len(data) < 3:
        width = 0.95
        pylab.bar(range(len(data)), [max(y, 0.01) for x, y in data], 0.95, color="g")
        pylab.xticks([i+0.5*width for i in range(len(data))], [x for x, y in data])
        pylab.yticks([0, 10, 20, 30, 40, 50])
    else:
        pylab.pie([max(y, 0.1) for x, y in data], labels=[x for x, y in data], autopct="%.0f%%")
    pylab.savefig(fname, format="png", dpi=75)
    pylab.close()


def evaluate(survey_dir, target_dir):
    questions, answers = collect_questions(survey_dir)
    try:
        os.mkdir(target_dir)
    except OSError, ex:
        pass # might already exist
    try:
        os.listdir(target_dir)
    except OSError, ex:
        print "cannot create target directory:", target_dir
        return False
    with open(os.path.join(target_dir, "report.html"), "wb") as report:
        report.write("""
        <html>
        <head>
        <meta http-equiv="content-type" content="application/xhtml+xml; charset=UTF-8" />
        </head>
        <body>
        """)
        report.write("<h1> Umfrage 2015 </h1>\n")
        report.write("\n\n")

        for idx, (q, a) in enumerate(zip(questions, answers)):

            if q["type"] in ("text-only", "votecode"):
                continue # not really a question, per se

            print "question: (%s)" % q["type"], q["question"][:60]

            report.write("<h2> \"%s\" </h2>\n\n" % q["question"].encode("utf8"))
            answers, comments = evaluate_question(q, a)

            if answers:
                rows = [u"Frage",] + q["subquestions"]
                cols = [u"Frage",] + [choice for choice, count in answers[0]]
                cell_len = map(len, cols)
                cell_len[0] = max(map(len, rows))
                fmt = "%%-%is" % cell_len[0]
                cols[0] = fmt % cols[0]
                report.write("<table border=\"1\">\n")
                line = "<tr> <th>" + " </th><th> ".join(cols) + "</th> </tr>"
                report.write(line.encode("utf8") + "\n")
                for i, subanswer in enumerate(answers):
                    cells = [ ]
                    fmt = "%%-%is" % cell_len[0]
                    cells.append(fmt % rows[i+1])
                    for choice, count in subanswer:
                        fmt = "%%%ii" % len(choice)
                        cells.append(fmt % int(count))
                    line = "<tr> <td>" + " </td><td> ".join(cells) + "</td> </tr>"
                    report.write(line.encode("utf8") + "\n")
                    report.write("</tr>\n")
                report.write("</table>\n")
            report.write("\n\n")

            # some nice pics
            report.write("<h3> Abbildungen </h3>\n\n")
            for i, subanswer in enumerate(answers):
                basename = "fig_%02i_%02i.png" % (idx, i)
                fname = os.path.join(target_dir, basename)
                title = q["subquestions"][i]
                plot_question(fname, title, subanswer)
                report.write("<img src=\"%s\">\n" % basename)
            report.write("\n\n")

            # comments section, if any
            if comments:
                report.write("<h3> Anmerkungen </h3>\n")
                report.write("<ul>\n")
                for comment in comments:
                    try:
                        report.write(" <li> %s </li>\n" % comment.strip().replace("\r", "").replace("\n", ". ").encode("utf8"))
                    except (UnicodeDecodeError, UnicodeEncodeError), ex:
                        print "ERROR IN COMMENT!", ex, repr(comment)
                        pass
                        #raise ex
                report.write("</ul>\n\n")
        report.write("</body>\n<html>\n\n")
    return True

