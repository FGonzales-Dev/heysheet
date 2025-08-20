import type { FC } from 'react';
import clsx from 'clsx';
import type { Message as MessageType } from '../types/chat';

interface MessageProps {
  message: MessageType;
}

export const Message: FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={clsx(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-900'
        )}
      >
        <p className="text-sm">{message.content}</p>
        <p className="text-xs mt-1 opacity-70">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};
