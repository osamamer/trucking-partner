import React, {useEffect, useRef} from "react";
import type {RouteData} from '../App.tsx';
import  {MAPBOX_TOKEN} from '../App.tsx';

export const MapboxRouteMap: React.FC<{ route: RouteData }> = ({route}) => {
    const mapContainer = useRef<HTMLDivElement>(null);
    const map = useRef<any>(null);

    useEffect(() => {
        if (!mapContainer.current || map.current) return;

        // Check if mapboxgl is available
        if (typeof window === 'undefined' || !(window as any).mapboxgl) {
            console.error('Mapbox GL JS not loaded');
            return;
        }

        const mapboxgl = (window as any).mapboxgl;
        mapboxgl.accessToken = MAPBOX_TOKEN;

        // Initialize map
        map.current = new mapboxgl.Map({
            container: mapContainer.current,
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [-98.5795, 39.8283], // Center of US
            zoom: 4
        });

        map.current.on('load', () => {
            // Create route coordinates
            const coordinates = route.stops
                .filter(stop => stop.location.latitude !== 0 && stop.location.longitude !== 0)
                .map(stop => [stop.location.longitude, stop.location.latitude]);

            // Add route line
            map.current.addSource('route', {
                type: 'geojson',
                data: {
                    type: 'Feature',
                    properties: {},
                    geometry: {
                        type: 'LineString',
                        coordinates: coordinates
                    }
                }
            });

            map.current.addLayer({
                id: 'route',
                type: 'line',
                source: 'route',
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round'
                },
                paint: {
                    'line-color': '#f97316',
                    'line-width': 4,
                    'line-opacity': 0.8
                }
            });

            // Add markers for each stop
            route.stops.forEach((stop, index) => {
                if (stop.location.latitude === 0 && stop.location.longitude === 0) return;

                // Create custom marker element
                const el = document.createElement('div');
                el.className = 'custom-marker';
                el.style.width = '32px';
                el.style.height = '32px';
                el.style.borderRadius = '50%';
                el.style.display = 'flex';
                el.style.alignItems = 'center';
                el.style.justifyContent = 'center';
                el.style.fontSize = '18px';
                el.style.cursor = 'pointer';
                el.style.border = '2px solid white';
                el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';

                // Set marker color and icon based on stop type
                const markerStyles: Record<string, { bg: string; icon: string }> = {
                    current: {bg: '#3b82f6', icon: '🚛'},
                    pickup: {bg: '#10b981', icon: '📦'},
                    dropoff: {bg: '#ef4444', icon: '🏁'},
                    fuel: {bg: '#f59e0b', icon: '⛽'},
                    '30min_break': {bg: '#8b5cf6', icon: '☕'},
                    '10hr_break': {bg: '#6366f1', icon: '🛏️'}
                };

                const style = markerStyles[stop.stop_type] || {bg: '#6b7280', icon: '📍'};
                el.style.backgroundColor = style.bg;
                el.innerHTML = style.icon;

                // Create popup
                const popup = new mapboxgl.Popup({offset: 25}).setHTML(`
                    <div style="color: #1f2937; min-width: 200px;">
                        <h3 style="font-weight: bold; margin-bottom: 4px; color: #f97316;">
                            ${stop.stop_type_display}
                        </h3>
                        <p style="font-size: 14px; margin-bottom: 8px;">${stop.location.address}</p>
                        <p style="font-size: 12px; color: #6b7280;">${stop.description}</p>
                        <p style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                            Arrive: ${new Date(stop.arrival_time).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                })}
                        </p>
                        ${stop.duration_minutes > 0 ? `
                            <p style="font-size: 12px; color: #6b7280;">
                                Depart: ${new Date(stop.departure_time).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                })}
                            </p>
                        ` : ''}
                    </div>
                `);

                new mapboxgl.Marker(el)
                    .setLngLat([stop.location.longitude, stop.location.latitude])
                    .setPopup(popup)
                    .addTo(map.current);
            });

            // Fit map to show all markers
            if (coordinates.length > 0) {
                const bounds = coordinates.reduce((bounds, coord) => {
                    return bounds.extend(coord as [number, number]);
                }, new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]));

                map.current.fitBounds(bounds, {
                    padding: 50,
                    maxZoom: 8
                });
            }
        });

        return () => {
            if (map.current) {
                map.current.remove();
                map.current = null;
            }
        };
    }, [route]);

    return (
        <div
            ref={mapContainer}
            className="w-full h-[600px] rounded-xl overflow-hidden border-2 border-orange-500/30"
        />
    );
};