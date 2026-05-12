import React, { useEffect, useMemo } from 'react';
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react';
import { Editor } from '@milkdown/core';
import { commonmark } from '@milkdown/preset-commonmark';
import { nord } from '@milkdown/theme-nord';

const EditorInstance = () => {
  const { get } = useEditor((root) =>
    Editor.make()
      .config((ctx) => {
        ctx.set(root, root);
      })
      .config(nord)
      .use(commonmark)
  );

  return <Milkdown />;
};

const MindPalaceEditor = () => {
  return (
    <div className="w-full h-full bg-white/5 rounded-2xl p-8 overflow-y-auto custom-scrollbar border border-white/5">
        <h2 className="text-xl font-black text-cyan-400 mb-6 tracking-tighter uppercase">MindPalace // Workspace</h2>
        <div className="prose prose-invert max-w-none">
            <MilkdownProvider>
                <EditorInstance />
            </MilkdownProvider>
        </div>
    </div>
  );
};

export default MindPalaceEditor;
