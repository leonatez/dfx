# 📊 Excel Automation Processor

Tired of manually cleaning and transforming Excel files?  
**Excel Automation Processor** is your no-code sidekick to automate repetitive Excel tasks — clean, merge, filter, group, and transform Excel files effortlessly in a few clicks.

Built with ❤️ using **Streamlit** + **Pandas**.

---

## 🚀 Features

- ✅ **No-Code UI**: Intuitive interface to define actions — no Python knowledge required  
- ✅ **Multi-file Support**: Process batches of Excel files grouped by format/template  
- ✅ **Workflow Builder**: Stack up actions like renaming, filtering, merging, and more  
- ✅ **Reusable Workflows**: Save and load workflows as JSON templates  
- ✅ **Preview & Download**: Instantly preview changes and download results as Excel or CSV  
- ✅ **Template Library**: One-click templates for cleaning, sales analysis, and standardization

---

## 🧠 How It Works

1. **Group Files**  
   Upload Excel files with the same format. Define sheet name, header row/column, and group them logically.

2. **Define Actions**  
   Pick from 10+ transformation types:
   - Rename columns
   - Change data types
   - Filter by values
   - Create new columns with formulas
   - Merge with other groups
   - Sort, group, aggregate, and more

3. **Run & Export**  
   Run all actions with a single click. Preview results, check stats, and export them as Excel or CSV.

---

## 🛠️ Tech Stack

- **Streamlit** – Frontend app engine  
- **Pandas** – Data processing  
- **OpenPyXL** – Excel export  
- **Numpy** – Numerical operations  
- **JSON** – Workflow storage  

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/leonatez/dfx.git
cd dfx

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run main.py
