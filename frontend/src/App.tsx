import { useEffect, useState } from 'react';
import { type Note, fetchNotes, createNote, deleteNote } from './api';

function App() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    fetchNotes().then(setNotes);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newNote = await createNote({ title, description });
    setNotes([...notes, newNote]);
    setTitle('');
    setDescription('');
  };

  const handleDelete = async (id: number) => {
    await deleteNote(id);
    setNotes(notes.filter(note => note.id !== id));
  };

  return (
    <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h1>Notes App</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
        <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" required />
        <br />
        <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Description" required />
        <br />
        <button type="submit">Add Note</button>
      </form>

      {notes.map(note => (
        <div key={note.id} style={{ marginBottom: 10 }}>
          <strong>{note.title}</strong>
          <p>{note.description}</p>
          <button onClick={() => handleDelete(note.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

export default App;
