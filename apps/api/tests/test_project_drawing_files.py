from test_known_takeoff_workflow import workflow, prepare


def test_project_drawing_files_are_scoped(workflow):
    client=workflow
    project_id,file_id,_=prepare(client)
    files = client.get(f'/projects/{project_id}/drawing-files')
    assert [f['id'] for f in files.json()] == [file_id]
    other = client.post('/projects', json={'name': 'Other project'}).json()['id']
    assert client.get(f'/projects/{other}/drawing-files').json() == []
    assert client.get('/projects/99999/drawing-files').status_code == 404
