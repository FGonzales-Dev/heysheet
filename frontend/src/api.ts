const API_URL = import.meta.env.VITE_API_URL;

export type Note = {
  id: number;
  title: string;
  description: string;
};

export async function fetchNotes(): Promise<Note[]> {
  const res = await fetch(`${API_URL}/api/notes/`);
  return await res.json();
}

export async function createNote(note: Omit<Note, 'id'>) {
  const res = await fetch(`${API_URL}/api/notes/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(note),
  });
  return await res.json();
}

export async function deleteNote(id: number) {
  await fetch(`${API_URL}/api/notes/${id}/`, { method: 'DELETE' });
}
