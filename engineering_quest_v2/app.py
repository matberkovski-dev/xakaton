@app.route('/api/admin/add_assignment', methods=['POST'])
def admin_add_assignment():
    u = current_user()
    if not u or u['Role'] != 'Администратор': return jsonify({'ok': False})
    d = request.get_json() or {}
    with db() as c:
        c.execute("INSERT INTO Assignments(Class,Subject,Question,Image,Answer,Price) VALUES(?,?,?,?,?,?)",
                  (d['class'], d['subject'], d.get('question',''), '', d['answer'], int(d.get('price',30))))
        aid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({'ok': True, 'id': aid})
