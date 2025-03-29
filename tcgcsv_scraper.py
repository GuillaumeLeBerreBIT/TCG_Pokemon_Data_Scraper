from requests_html import HTMLSession
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import os 
import time
import csv
import sqlite3

class TCGCSVScraper:
    
    def __init__(self, output_dir='csv_downloads'):
        """
        Initialize the TCGCSVScraper with configurable base URL and output directory.
        
        Args:
            base_url (str): The base URL to scrape from
            output_dir (str): Directory to save downloaded CSV files
        """
        self.url = 'https://tcgcsv.com/'
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        self.output_dir = output_dir
        self.db = 'pokemontcg.db'
        
        # Initialize database
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()
        self.create_table()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
    def render_js(self):
        """Render JavaScript content on the page and return the full HTML."""
        session = HTMLSession()
        r = session.get(self.url)
        r.html.render(sleep=2)
        response = r.html.html
        
        return response
        
    def create_soup_obj(self, response):
        """
        Parse HTML and extract relevant data rows.
        
        Returns:
            list: Data rows containing Pokemon card information
        """
        soup = BeautifulSoup(response, 'html.parser')
        details = soup.find_all('details')
        
        data = []
        for d in details:
            if 'POKEMON' in d.summary.text.upper():
                tables = d.find_all('table')
                for t in tables:
                    rows = t.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if cols:
                            data.append(cols)
        
        return data
    
    def find_csv(self, data):
        """
        Extract CSV download links from the data rows.
        
        Returns:
            dict: Dictionary mapping set names to their download links
        """
        csv_dict = {}
        for row in data:
            set_id = row[1].text.strip()
            set_name = row[0].text.strip()
            
            for child in row[2].contents:
                if hasattr(child, 'text') and 'CSV' in child.text.upper():
                    if hasattr(child, 'attrs') and 'href' in child.attrs:
                        csv_endpoint = child.attrs["href"]
                        if set_id not in csv_dict:
                            csv_dict[set_id] = {}
                        csv_dict[set_id][set_name] = csv_endpoint
        
        return csv_dict
    
    def parse_csv_data(self, csv_dict):
        
        csv_data = {}
        for set_id, set_info in csv_dict.items():
            for set_name, endpoint in set_info.items():
                # Construct full URL
                full_url = urljoin(self.url, endpoint)
                
                try:
                    response = requests.get(full_url, headers=self.headers)
                    response.raise_for_status()
                    
                    # Parse CSV content 
                    decoded_content = response.content.decode('utf-8')
                    csv_reader = csv.reader(decoded_content.splitlines())
                    rows = list(csv_reader)
                    
                    # Parse in the data to the SQL function
                    if rows:
                        self.insert_data_with_mapping(set_name, set_id, rows)
                        
                                        
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch {full_url}: {str(e)}")
                    
                finally:
                    csv_data[set_name] = rows
                    
        return csv_data
    
    def insert_data_with_mapping(self, set_name, set_id, rows):
        # Prepare the data to send to the database. Create list of tuples 
        
        if len(rows) <= 1:
            print(f"No data to insert for {set_name}")
            return 
        
        csv_header = [col.lower() for col in rows[0]]
        
        db_columns = self.return_column_names()
        
        column_mapping = {}
        for db_col in db_columns:
            # Try to find matching column in CSV (case-insensitive)
            db_col_lower = db_col.lower()
            
            # Check for exact match first
            if db_col_lower in csv_header:
                # The Key is the column name & The value is the index of the column in the rows list/array.
                column_mapping[db_col] = csv_header.index(db_col_lower)
            # Try partial match
            else:
                matches = [i for i, col in enumerate(csv_header) if db_col_lower in col]
                if matches:
                    column_mapping[db_col] = matches[0]
        
        print(f"Found mappings for {len(column_mapping)} out of {len(db_columns)-2} columns")
        
        try:
            
            for row in rows[1:]:
                
                row_data = {'setName': set_name, 'setId': set_id}
                
                # Map values from CSV to appropriate database columns
                for col_db, csv_index in column_mapping.items():
                    if csv_index < len(row):
                        # Fil in the row dictionary with key as volumn name and data as value, using the index to find the value matching the column name in the row data.
                        row_data[col_db] = row[csv_index]
                        
                # Fill in missing columns with empty strings
                for col_db in db_columns:
                    if col_db not in row_data:
                        row_data[col_db] = ""
                            
                # ordered_values = [row_data['setName'], row_data['setId']]
                # Retrieve the values from the dictionary.
                ordered_values = [row_data[col] for col in db_columns]
                test_tuple= tuple(ordered_values)     
                print(f'The {set_name} trying to inject into the database.')
                self.cursor.execute("""
                    INSERT INTO pokemon VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?
                    )
                """, tuple(ordered_values))
                # Either commit the changes when all is succesfull.
                self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            # Rollback the changes if something occured in the above try statement.
            self.conn.rollback()
    
    def close(self):
        self.conn.close()
        
    def return_column_names(self):
        """
        Return the headers of the database
        """
        data = self.cursor.execute("""
                             SELECT * FROM pokemon LIMIT 1
                             """)
        headers = []
        for col in data.description:
            
            if col not in headers:
                headers.append(col[0])
            
        return headers
        
    
    def create_table(self):
        """
        Create table to contain the data
        """
        self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pokemon (
                        setName TEXT,
                        setId INTEGER,
                        productId TEXT,
                        name TEXT,
                        cleanName TEXT,
                        imageUrl TEXT,
                        categoryId TEXT,
                        groupId TEXT,
                        url TEXT,
                        modifiedOn TEXT,
                        imageCount INTEGER,
                        extNumber TEXT,
                        extRarity TEXT,
                        extCardType TEXT,
                        extHP TEXT,
                        extStage TEXT,
                        extCardText TEXT,
                        extAttack1 TEXT,
                        extWeakness TEXT,
                        extRetreatCost TEXT,
                        lowPrice REAL,
                        midPrice REAL,
                        highPrice REAL,
                        marketPrice REAL,
                        directLowPrice REAL,
                        subTypeName TEXT,
                        extAttack2 TEXT,
                        extResistance TEXT,
                        extAttack3 TEXT
                    )
                    """)       
                    
    
    def parser(self, save_to_file=True):
        """
        Main method to run the entire scraping process.
        
        Args:
            save_to_file (bool): Whether to save the CSV data to files
            
        Returns:
            dict: Dictionary containing all parsed CSV data
        """
        response = self.render_js()
        data = self.create_soup_obj(response)
        csv_dict = self.find_csv(data)
        csv_data = self.parse_csv_data(csv_dict)
        
        self.close()
        
        
        