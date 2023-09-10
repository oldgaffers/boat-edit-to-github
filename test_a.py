from boat_edit_to_github.lambda_function import get_members_by_name, owner_record

members = [
        {'Firstname': 'A', 'Lastname': 'Bird', 'ID': 1, 'Member Number': 1},
        {'Firstname': 'A', 'Lastname': 'Bird', 'ID': 2, 'Member Number': 2},
        {'Firstname': 'A', 'Lastname': 'Cat', 'ID': 3, 'Member Number': 3},
    ]

def test_get_members_by_name():
    assert get_members_by_name('A FISH', members) == []
    assert get_members_by_name('A CAT', members) == [{'id': 3, 'member': 3}]
    assert get_members_by_name('A BIRD', members) == [{'id': 1, 'member': 1}, {'id': 2, 'member': 2},]

def test_owner_record():
    assert owner_record({ 'ID': 1 }, members) == { 'id': 1 }
    assert owner_record({ 'ID': 1, 'name': 'Dr Who' }, members) == { 'id': 1 }
    assert owner_record({ 'name': 'a cat' }, members) == { 'id': 3, 'member': 3 }
    assert owner_record({ 'name': ' a cat' }, members) == { 'id': 3, 'member': 3 }
    assert owner_record({ 'share': 64, 'name': 'a cat' }, members) == { 'share': 64, 'id': 3, 'member': 3 }

