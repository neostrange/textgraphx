from textgraphx.TlinksRecognizer import TlinksRecognizer

tr = TlinksRecognizer()
# create_tlinks_e2t(doc_id="61327")
print("Executing E2E...")
tr.create_tlinks_e2e("61327", precision_mode=False)
print("Executing E2T...")
tr.create_tlinks_e2t("61327", precision_mode=False)
print("Executing T2T...")
tr.create_tlinks_t2t("61327", precision_mode=False)

