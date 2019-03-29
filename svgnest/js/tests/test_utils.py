from svgnest.js.utils import splice


def test_splice():
    mesPoissons = ["scalaire", "clown", "mandarin", "chirurgien"]

    # supprime 0 élément à partir de l'index 2, et insère "tambour"
    enleves = splice(mesPoissons, 2, 0, "tambour")
    assert mesPoissons == ["scalaire", "clown", "tambour", "mandarin", "chirurgien"]
    assert enleves == []

    enleves = splice(mesPoissons, 3, 1)
    assert mesPoissons == ["scalaire", "clown", "tambour", "chirurgien"]
    assert enleves == ["mandarin"]

    # supprime 1 élément à partir de l'index 2, et insère "trompette"
    enleves = splice(mesPoissons, 2, 1, "trompette")
    assert mesPoissons == ["scalaire", "clown", "trompette", "chirurgien"]
    assert enleves == ["tambour"]

    # supprime 2 éléments à partir de l'index 0, et insère "perroquet", "anémone" et"bleu"
    enleves = splice(mesPoissons, 0, 2, "perroquet", "anémone", "bleu")
    assert mesPoissons == ["perroquet", "anémone", "bleu", "trompette", "chirurgien"]
    assert enleves == ["scalaire", "clown"]

    # supprime 2 éléments à partir de l'indice 2
    enleves = splice(mesPoissons, len(mesPoissons) - 3, 2)
    assert mesPoissons == ["perroquet", "anémone", "chirurgien"]
    assert enleves == ["bleu", "trompette"]

    mesPoissons = ["perroquet", "anémone", "bleu", "trompette", "chirurgien"]
    # on retire trois éléments à partir de l'indice 2
    enleves = splice(mesPoissons, 2)
    assert mesPoissons == ["perroquet", "anémone"]
    assert enleves == ["bleu", "trompette", "chirurgien"]

    mesAnimaux = ["cheval", "chien", "chat", "dauphin"]
    enleves = splice(mesAnimaux, -2, 1)

    assert mesAnimaux == ["cheval", "chien", "dauphin"]
    assert enleves == ["chat"]
