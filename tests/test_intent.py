from orbit.agent.intent import guess_language, parse_intent


def test_open_app_english():
    intent = parse_intent("Orbit, open Chrome")
    assert intent.action == "open_app"
    assert intent.entities["app"] == "Google Chrome"


def test_create_folder_preserves_case():
    intent = parse_intent("create a folder called Buyer Leads")
    assert intent.action == "create_folder"
    assert intent.entities["folder_name"] == "Buyer Leads"


def test_hinglish_command():
    intent = parse_intent("Chrome kholo aur Gmail check karo")
    assert intent.action in ("open_app", "read_email")
    assert intent.language_guess in ("hi", "hinglish")


def test_stop_command_variants():
    assert parse_intent("Orbit, stop").action == "stop"
    assert parse_intent("ruko").action == "stop"


def test_cancel_send_beats_send():
    intent = parse_intent("don't send it")
    assert intent.action == "cancel_send"


def test_switch_chrome_profile_extracts_name():
    intent = parse_intent("switch to Vrindavan Organics profile")
    assert intent.action == "switch_chrome_profile"
    assert intent.entities["profile_name"] == "Vrindavan Organics"


def test_switch_chrome_profile_to_phrasing():
    intent = parse_intent("switch profile to Rahul Soni")
    assert intent.action == "switch_chrome_profile"
    assert intent.entities["profile_name"] == "Rahul Soni"


def test_send_command():
    intent = parse_intent("send it")
    assert intent.action == "send"


def test_unknown_command_low_confidence():
    intent = parse_intent("asdkjaslkdj qqweqwe")
    assert intent.action == "unknown"
    assert intent.confidence < 0.5


def test_guess_language_devanagari():
    assert guess_language("नमस्ते खोलो") == "hi"


def test_guess_language_english():
    assert guess_language("open chrome please") == "en"


def test_search_query_extraction_preserves_case():
    intent = parse_intent("search for Ekagya Exports")
    assert intent.action == "search"
    assert intent.entities["query"] == "Ekagya Exports"


def test_draft_email_extracts_recipient_body_and_subject():
    intent = parse_intent("draft email as hello testing to rahulsoni0857@gmail.com")
    assert intent.action == "draft_email"
    assert intent.entities["to"] == "rahulsoni0857@gmail.com"
    assert intent.entities["body"] == "hello testing"
    assert intent.entities["subject"] == "hello testing"


def test_draft_email_extracts_subject_from_about_clause():
    intent = parse_intent("draft an email about the quotation to buyer@example.com")
    assert intent.entities["to"] == "buyer@example.com"
    assert intent.entities["subject"] == "the quotation"


def test_draft_email_without_recipient_has_no_to_entity():
    intent = parse_intent("draft an email")
    assert intent.action == "draft_email"
    assert "to" not in intent.entities


def test_summarize_extracts_file_and_folder_hint():
    intent = parse_intent("open this camscanner pdf in downloads and summarize it")
    assert intent.action == "summarize"
    assert intent.entities["file_hint"] == "camscanner"
    assert intent.entities["folder_hint"] == "downloads"


def test_summarize_without_named_file_has_no_hint():
    intent = parse_intent("open this PDF and summarize it")
    assert intent.action == "summarize"
    assert "file_hint" not in intent.entities
