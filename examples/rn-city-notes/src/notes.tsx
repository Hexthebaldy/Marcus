import { createContext, useContext, useState, type ReactNode } from "react";

export type Note = { id: string; title: string; body: string };

const initialNotes: Note[] = [
  {
    id: "1",
    title: "在徐汇滨江走一走",
    body: "傍晚沿着江边慢慢走。\n\n带一瓶水，找张长椅坐下，看船经过。",
  },
  {
    id: "2",
    title: "周末去看一个展览",
    body: "今天留出两个小时看展。\n\n把喜欢的作品记下来，回家再查作者的其他作品。",
  },
];

type NotesValue = {
  notes: Note[];
  addNote: (title: string, body: string) => void;
};

const NotesContext = createContext<NotesValue | null>(null);

export function NotesProvider({ children }: { children: ReactNode }) {
  // 放在所有页面外面：切换页面时，这份列表仍然保留。
  const [notes, setNotes] = useState(initialNotes);

  function addNote(title: string, body: string) {
    const note = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      title,
      body,
    };
    setNotes((previousNotes) => [note, ...previousNotes]);
  }

  return (
    <NotesContext.Provider value={{ notes, addNote }}>
      {children}
    </NotesContext.Provider>
  );
}

export function useNotes() {
  const value = useContext(NotesContext);
  if (!value) throw new Error("页面必须放在 NotesProvider 内部");
  return value;
}
