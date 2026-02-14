/**
 * Skeleton loading component.
 * Provides placeholder UI while content is loading.
 */
import React from 'react';
import { cn } from '../../lib/utils';

/**
 * Base skeleton component with pulsing animation.
 */
function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn(
        "animate-pulse bg-gray-200 border-2 border-gray-300",
        className
      )}
      {...props}
    />
  );
}

/**
 * Skeleton for a single line of text.
 */
function SkeletonText({ width = "w-full", className }) {
  return (
    <Skeleton className={cn("h-4", width, className)} />
  );
}

/**
 * Skeleton for a user card/row.
 */
function SkeletonUserCard({ className }) {
  return (
    <div className={cn("p-3 border-2 border-gray-300 bg-white", className)}>
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-sm" />
        <div className="flex-1 space-y-2">
          <SkeletonText width="w-1/2" />
          <SkeletonText width="w-1/3" />
        </div>
        <Skeleton className="w-16 h-8" />
      </div>
    </div>
  );
}

/**
 * Skeleton for a list of users.
 * @param {number} count - Number of skeleton cards to show
 */
function SkeletonUserList({ count = 5, className }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonUserCard key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton for statistics card.
 */
function SkeletonStatsCard({ className }) {
  return (
    <div className={cn("p-4 border-2 border-gray-300 bg-white", className)}>
      <Skeleton className="h-4 w-20 mb-2" />
      <Skeleton className="h-8 w-16" />
    </div>
  );
}

/**
 * Skeleton for schedule item.
 */
function SkeletonScheduleItem({ className }) {
  return (
    <div className={cn("p-3 border-2 border-gray-300 bg-white", className)}>
      <div className="flex items-center gap-3">
        <Skeleton className="w-12 h-12 rounded-sm" />
        <div className="flex-1 space-y-2">
          <SkeletonText width="w-3/4" />
          <SkeletonText width="w-1/2" />
          <SkeletonText width="w-1/4" />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton for schedule list.
 * @param {number} count - Number of skeleton items to show
 */
function SkeletonScheduleList({ count = 4, className }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonScheduleItem key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton for admin panel header stats.
 */
function SkeletonAdminStats({ className }) {
  return (
    <div className={cn("grid grid-cols-2 gap-2", className)}>
      {Array.from({ length: 4 }).map((_, i) => (
        <SkeletonStatsCard key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton for chart/graph.
 */
function SkeletonChart({ className }) {
  return (
    <div className={cn("p-4 border-2 border-gray-300 bg-white", className)}>
      <Skeleton className="h-4 w-32 mb-4" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}

/**
 * Skeleton for table row.
 */
function SkeletonTableRow({ columns = 4, className }) {
  return (
    <div className={cn("flex items-center gap-2 p-2 border-b border-gray-200", className)}>
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} className="h-4 flex-1" />
      ))}
    </div>
  );
}

/**
 * Skeleton for table.
 * @param {number} rows - Number of skeleton rows to show
 * @param {number} columns - Number of columns per row
 */
function SkeletonTable({ rows = 5, columns = 4, className }) {
  return (
    <div className={cn("border-2 border-gray-300 bg-white", className)}>
      {/* Header */}
      <div className="flex items-center gap-2 p-2 bg-gray-100 border-b-2 border-gray-300">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1 bg-gray-300" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonTableRow key={i} columns={columns} />
      ))}
    </div>
  );
}

export {
  Skeleton,
  SkeletonText,
  SkeletonUserCard,
  SkeletonUserList,
  SkeletonStatsCard,
  SkeletonScheduleItem,
  SkeletonScheduleList,
  SkeletonAdminStats,
  SkeletonChart,
  SkeletonTableRow,
  SkeletonTable,
};
