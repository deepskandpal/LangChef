const fetch = require('node-fetch');
const fs = require('fs');

async function main() {
  try {
    // Read the CSV file
    const csvContent = fs.readFileSync('./test.csv', 'utf8');
    
    // Parse CSV to JSON
    const lines = csvContent.split('\n');
    const headers = lines[0].split(',');
    const items = [];
    
    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      
      const values = lines[i].split(',');
      const item = {};
      
      for (let j = 0; j < headers.length; j++) {
        item[headers[j].trim()] = values[j]?.trim() || '';
      }
      
      items.push(item);
    }
    
    // Create the dataset with the CSV items
    const response = await fetch('http://localhost:8001/api/datasets/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: 'test_csv_from_script',
        description: 'Testing CSV upload via Node.js script',
        dataset_type: 'csv',
        items: items
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error:', response.status, errorText);
      return;
    }
    
    const data = await response.json();
    console.log('Success! Created dataset:', data);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main(); 