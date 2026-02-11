"use client";

/**
 * Print header for reporting page
 * Displays company name, report title, and date range
 * Only visible in print mode
 */
export function PrintHeader() {
  const today = new Date().toLocaleDateString("cs-CZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="hidden print:block mb-8 border-b-2 border-gray-900 pb-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">INFERBOX</h1>
          <p className="text-lg text-gray-700 mt-1">Analytické reporty</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600">Vygenerováno:</p>
          <p className="text-base font-medium">{today}</p>
        </div>
      </div>
    </div>
  );
}
