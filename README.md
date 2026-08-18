# **Smart University Schedule (SUS)**

## **Project Overview**

The Smart University Schedule (SUS) is an intelligent scheduling system designed to revolutionize university timetabling. It leverages hybrid optimization algorithms (including BBO, GA, and SA) to generate conflict-free schedules, effectively resolving common academic scheduling challenges. The system provides a seamless, interactive platform for both administrators and faculty members to manage, request, and approve class slots in real-time.

## **Key Features**

* **Intelligent Optimization Engine:** Generates conflict-free schedules using hybrid AI optimization algorithms (BBO, GA, and SA).
* **Admin Dashboard:**
    * **Registry Visualization:** Full view of the academic registry with multi-filter options (Department, Term).
    * **Live Conflict Detection:** Real-time identification and highlighting of room and instructor booking conflicts.
    * **Request Management:** Centralized system to Approve or Reject incoming class slot requests with custom feedback notes.
    * **Interactive Time-Grid:** A dynamic, searchable visual grid for immediate schedule assessment.
    * **Data Export:** Secure CSV export capabilities for both filtered search results and the full academic registry.
* **Instructor Portal:**
    * **Personalized Schedule:** Instructors can view their specific courses and assigned slots.
    * **Dynamic Slot Requesting:** Faculty can request new class slots with automatic "Room Availability" checking based on real-time data.
    * **Status Tracking:** Real-time feedback loop showing the status of requests (Pending, Approved, or Rejected) with administrative notes.
* **Visitor Portal:**
    * **Public Schedule Browsing:** Allows students and guests to view university schedules and course offerings in a user-friendly, read-only interface.
    * **Search & Filter:** Easily find courses by subject, department, or instructor without needing authentication.
* **Authentication & Communication:**
    * **Secure Access:** Dedicated login/auth system for administrators and faculty.
    * **Contact Interface:** An integrated contact page for support and feedback, synchronized with the system's database.
* **Data Integrity & Pipeline:**
    * **Real-time Request Pipeline:** Persistent storage and synchronization between the Flask backend and the CSV database.
    * **Data Mapping:** Seamless integration of class sections, room capacities, and course codes directly into the interface.
* **Analytical Support:** Visual load charts for class distribution across the week to assist in administrative decision-making.

## **Technical Stack**

* **Frontend:** HTML5, Bootstrap 5, CSS3, JavaScript (ES6+).  
* **Backend:** Python (Flask).  
* **Data Processing:** Pandas (for Excel/CSV management).  
* **Optimization Core:** Python-based algorithms (stored in optimizationCodes/).  
* **Grid Engine:** A custom-built JavaScript Time-Grid Engine (SUS v7.0) for high-precision scheduling.

## **Project Structure**

SUS3\_PROJECT/  
├── app.py                \# Main Flask server application  
├── data/                 \# Academic data (Excel files)  
├── optimizationCodes/    \# AI optimization algorithms (BBO, GA, SA)  
├── static/  
│   ├── css/              \# Styling sheets  
│   ├── js/               \# Frontend logic (Admin, Instructor, TimeGrid Engine)  
│   └── images/           \# Assets and logos  
├── templates/            \# HTML user interfaces  
└── instructor\_slots\_requests.csv \# Real-time request database.  
    

## **Setup and Execution**

To run the project, ensure you have Python 3 installed. Follow these steps:

1. **Install Dependencies:** Open your terminal in the project directory and run:  
   pip install flask flask-cors pandas  
2. **Launch the Application:** Run the following command:  
   python3 app.py  
3. **Access the System:** Open your web browser and navigate to: [http://127.0.0.1:5001](http://127.0.0.1:5001)

## **Team**

* **Student:** Ibtihal Fallatah, Roaa Almadani, Sadan Abuouf, Shatha Mahrous, Lama Wassabi.
* **Student:** Dr.Abdelaziz Hammouri, Dr.Rami Jomaa.
* **Major:** Artificial Intelligence  
* **Institution:** Prince Mugrin University
