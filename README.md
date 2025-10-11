# TruckRoute - HOS-Compliant Route Planning

A route planning and ELD system for commercial truck drivers that ensures compliance with Hours of Service regulations.

## Features

- **Automatic Route Generation** with HOS-compliant breaks and rest periods
- **Interactive Map** with stop markers and route visualization
- **Daily ELD Logs** with 24-hour timeline grid
- **Smart Stop Planning**: 30-min breaks, 10-hour rest periods, fuel stops every 1,000 miles
- **Feasibility Checking**: Validates available hours in 70-hour/8-day cycle

## Tech Stack Used

**Backend**: Django, PostgreSQL, MapBox API  
**Frontend**: React, TypeScript, Tailwind CSS, MapBox GL JS

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

**Backend (.env)**
```
MAPBOX_ACCESS_TOKEN=your_token
DATABASE_URL=postgresql://user:pass@localhost/truckroute
TIME_ZONE=Asia/Amman
```

**Frontend (.env)**
```
VITE_API_URL=http://localhost:8000/api
VITE_MAPBOX_TOKEN=your_token
```


## API

- `POST /api/trips/` - Create trip
- `POST /api/trips/{id}/generate-route/` - Generate route
- `GET /api/trips/{id}/daily-logs/` - Get daily logs

