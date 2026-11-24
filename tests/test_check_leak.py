import importlib.util
from pathlib import Path


def module():
    spec = importlib.util.spec_from_file_location("lab3_leak", Path(__file__).parents[1] / "scripts/check_leak.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def record(user, assistant="дозволений текст документа"):
    return dict(src_split="corpus", src_doc_ids=["d"], messages=[dict(role="user", content=user),
                                                               dict(role="assistant", content=assistant)])


def test_exact_test_query_rejected_but_corpus_allowed():
    leak = module()
    query = dict(id="q1", input="яка ціна перевірки обладнання", expected="897 гривень", split="test")
    assert "q1" in str(leak.check([record(query["input"])], [query]))
    assert leak.check([record("опиши процедуру приймання станції")], [query]) == []
    assert "q1" in str(leak.check([record("other", query["expected"])], [query]))


def test_jaccard_boundary():
    leak = module()
    query = dict(id="q", input="a b c d e f g h i j", expected="unique truth", split="test")
    assert leak.similarity(query["input"], "a b c d e f g h i x") < leak.THRESHOLD
    assert leak.check([record("a b c d e f g h i x")], [query]) == []
    assert leak.similarity(query["input"], "j i h g f e d c b a") > leak.THRESHOLD
    assert leak.check([record("j i h g f e d c b a")], [query])
