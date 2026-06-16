"""Regression tests for title extraction heuristics."""

from core.metadata_extractor import extract_title_from_markdown


def test_h2_bold_lowercase_title_beats_author_line():
    """Regression: arXiv papers often render the title as '## **Title**' (H2 + bold) and
    the title may start lowercase (e.g. 'fMRI-S4'). The author line immediately below
    starts Uppercase. Before the fix, the title got no heading bonus (only H1 matched) and
    was penalized for starting lowercase, so the Uppercase author line outscored it."""
    md = (
        "## **fMRI-S4: learning short- and long-range dynamic fMRI dependencies "
        "using 1D Convolutions and State Space Models**\n\n"
        "Ahmed El-Gazzar[1] _[,]_[2] , Rajat Mani Thomas[1] _[,]_[2] , "
        "and Guido van Wingen[1] _[,]_[2]\n\n"
        "**Abstract.** Single-subject mapping of resting-state brain ...\n"
    )
    title = extract_title_from_markdown(md)
    assert title.lower().startswith("fmri-s4")
    assert "state space models" in title.lower()
    assert "el-gazzar" not in title.lower()  # must NOT be the author line


def test_plain_h1_title_still_works():
    md = "# A Transformer Approach to EEG Decoding\n\nJohn Smith, Jane Doe\n\nAbstract ...\n"
    assert extract_title_from_markdown(md) == "A Transformer Approach to EEG Decoding"


def test_bold_only_title_still_works():
    md = "**Deep State Space Models for Seizure Detection**\n\nAuthor One\n\nAbstract ...\n"
    assert extract_title_from_markdown(md) == "Deep State Space Models for Seizure Detection"
