# Smart University Scheduling System

## Overview

The **Smart University Scheduling System** is a graduation project developed to improve and simplify the process of creating university timetables.

Creating a university schedule can be challenging because it involves coordinating courses, instructors, classrooms, available time slots, and different scheduling requirements. Managing these factors manually can be time-consuming and may result in scheduling conflicts.

This project provides a smart approach to generating university schedules while considering the required constraints and available resources.

## Problem Statement

University scheduling requires coordinating a large number of courses, instructors, classrooms, and time slots. Manual scheduling can be difficult to manage and may lead to issues such as:

* Course conflicts
* Instructor scheduling conflicts
* Classroom conflicts
* Incorrect classroom capacity assignments
* Uneven distribution of courses
* Difficulty modifying existing schedules

The goal of this project is to make the scheduling process more efficient, organized, and easier to manage.

## Project Objectives

The main objectives of the project are to:

* Automate the university scheduling process.
* Reduce scheduling conflicts.
* Assign courses to suitable classrooms and time slots.
* Consider instructor availability.
* Improve the use of available university resources.
* Generate clear and organized timetables.
* Reduce the time required to create and modify schedules.

## Main Features

* Course and section management
* Instructor management
* Classroom management
* Time slot management
* Scheduling constraint management
* Automatic schedule generation
* Conflict detection
* Schedule visualization
* Schedule modification and management

## How It Works

The system follows several steps to generate the final schedule:

1. Collect the required scheduling information.
2. Define courses, instructors, classrooms, and available time slots.
3. Apply the required scheduling constraints.
4. Generate possible scheduling arrangements.
5. Check the generated schedules for conflicts.
6. Select a suitable schedule based on the defined requirements.
7. Display the final schedule in an organized format.

## Scheduling Constraints

The system considers different types of constraints when generating the schedule.

### Hard Constraints

Hard constraints are requirements that must be satisfied:

* An instructor cannot teach two courses at the same time.
* A classroom cannot be assigned to more than one course at the same time.
* A classroom must have enough capacity for the assigned course.
* Courses must be assigned to available time slots.
* Required course sessions must be included in the schedule.

### Soft Constraints

Soft constraints are preferences that help improve the quality of the generated schedule:

* Better distribution of courses throughout the week.
* Reducing unnecessary gaps between classes.
* Considering instructor preferences when possible.
* Improving classroom utilization.
* Creating a more balanced timetable.

## Technologies Used

* Python
* Artificial Intelligence
* Optimization Techniques
* Git & GitHub

## Project Structure

```text
Smart-University-Scheduling/
│
├── data/
├── src/
├── models/
├── notebooks/
├── tests/
├── requirements.txt
└── README.md
```

## Getting Started

### Requirements

Before running the project, make sure you have:

* Python 3.x
* Git
* The required Python libraries listed in `requirements.txt`

### Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
```

Move to the project directory:

```bash
cd YOUR-REPOSITORY
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Project

Run the main application using:

```bash
python main.py
```

> Replace `main.py` with the actual entry point of the project if your main file has a different name.

## Results

The system provides an automated approach to university timetable generation while considering the main scheduling requirements and constraints.

The generated schedules can be evaluated based on:

* Number of scheduling conflicts
* Constraint satisfaction
* Classroom utilization
* Instructor availability
* Overall schedule quality

## Project Screenshots

### Main Interface

Add a screenshot of the main interface here.

### Generated Schedule

Add a screenshot of the generated university schedule here.

## Future Improvements

Future versions of the system could include:

* Supporting larger and more complex university datasets.
* Adding more scheduling constraints and preferences.
* Improving the scheduling and optimization process.
* Adding detailed schedule analytics.
* Integrating the system with existing university information systems.
* Developing a mobile version of the system.
* Adding personalized schedules for students and instructors.

## Academic Project

This project was developed as a graduation project as part of the requirements for the **Bachelor's Degree in Artificial Intelligence**.

**Project:** Smart University Scheduling System
**Year:** 2026
**Program:** Artificial Intelligence
**University:** University of Prince Mugrin

## Team

This project was developed by:

* Shatha Mahrous
* Sadan Abuouf
* Lama Wassabi
* Ibtihal Fallatah
* Roaa Almdani

## Acknowledgments

We would like to thank our project supervisor, faculty members, and the **University of Prince Mugrin** for their guidance and support throughout the development of this project.

## License

This project was developed for academic purposes.
