import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-md bg-black/5 dark:bg-white/10 ${className || ''}`}
      {...props}
    />
  );
}
