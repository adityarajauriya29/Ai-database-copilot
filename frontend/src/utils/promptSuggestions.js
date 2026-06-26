export function generateSuggestions(schema) {
  if (!schema?.tables?.length) {
    return [
      "Show all tables",
      "List all records",
      "Show total number of rows",
      "Describe this database",
      "Show table relationships",
    ]
  }

  const tableNames = schema.tables.map((t) => t.name.toLowerCase())

  const prompts = []

  // ---------------- Ecommerce ----------------

  if (tableNames.includes("customers")) {
    prompts.push("Show top 10 customers by total spending")
    prompts.push("Show customers from Delhi")
  }

  if (tableNames.includes("products")) {
    prompts.push("Show products with stock less than 20")
    prompts.push("Show highest rated products")
  }

  if (tableNames.includes("orders")) {
    prompts.push("Show orders placed in the last 30 days")
    prompts.push("Show total revenue")
  }

  // ---------------- University ----------------

  if (tableNames.includes("students")) {
    prompts.push("Show students with CGPA above 8.5")
    prompts.push("Show students department wise")
  }

  if (tableNames.includes("courses")) {
    prompts.push("Show all 4 credit courses")
  }

  if (tableNames.includes("professors")) {
    prompts.push("Show professors with highest salary")
  }

  // ---------------- HR ----------------

  if (tableNames.includes("employees")) {
    prompts.push("Show average salary by department")
    prompts.push("Show employees hired this year")
  }

  if (tableNames.includes("attendance")) {
    prompts.push("Show attendance for this month")
  }

  // ---------------- Chinook ----------------

  if (tableNames.includes("album")) {
    prompts.push("Show all albums")
  }

  if (tableNames.includes("artist")) {
    prompts.push("Show artists with the most albums")
  }

  if (tableNames.includes("track")) {
    prompts.push("Show longest tracks")
    prompts.push("Show top 10 tracks")
  }

  if (tableNames.includes("invoice")) {
    prompts.push("Show top customers by invoice amount")
    prompts.push("Show revenue by country")
  }

  if (tableNames.includes("playlist")) {
    prompts.push("Show all playlists")
  }

  if (tableNames.includes("genre")) {
    prompts.push("Show tracks by genre")
  }

  return [...new Set(prompts)].slice(0, 8)
}