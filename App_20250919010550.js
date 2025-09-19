import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Progress } from "./components/ui/progress";
import { 
  Car, 
  Clock, 
  DollarSign, 
  TrendingUp, 
  MapPin, 
  Users,
  BarChart3,
  AlertTriangle,
  RefreshCw
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [hourlyData, setHourlyData] = useState([]);
  const [zoneData, setZoneData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dataLoaded, setDataLoaded] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      await axios.post(`${API}/ingest-taxi-data`);
      setDataLoaded(true);
      await fetchAnalytics();
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const [overviewRes, hourlyRes, zoneRes] = await Promise.all([
        axios.get(`${API}/analytics/overview`),
        axios.get(`${API}/analytics/hourly`),
        axios.get(`${API}/analytics/zones`)
      ]);
      
      setAnalytics(overviewRes.data);
      setHourlyData(hourlyRes.data);
      setZoneData(zoneRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await axios.get(`${API}/health`);
        await fetchAnalytics();
        setDataLoaded(true);
      } catch (error) {
        console.error('API health check failed:', error);
      } finally {
        setLoading(false);
      }
    };
    
    checkHealth();
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const getDelayStatusColor = (percentage) => {
    if (percentage > 30) return 'bg-red-500';
    if (percentage > 15) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const HourlyChart = ({ data }) => {
    const maxWaitTime = Math.max(...data.map(d => d.avg_wait_time));
    
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-12 gap-2 h-64">
          {data.map((item, index) => (
            <div key={index} className="flex flex-col items-center justify-end">
              <div className="text-xs text-gray-600 mb-1">
                {item.delay_percentage > 20 && (
                  <AlertTriangle className="w-3 h-3 text-red-500 mb-1" />
                )}
              </div>
              <div 
                className="w-full bg-blue-500 rounded-t transition-all duration-300 hover:bg-blue-600"
                style={{
                  height: `${(item.avg_wait_time / maxWaitTime) * 200}px`,
                  minHeight: '8px'
                }}
                title={`Hour ${item.hour}: ${item.avg_wait_time}min avg wait, ${item.delay_percentage}% delayed`}
              />
              <div className="text-xs mt-1 font-medium">
                {item.hour.toString().padStart(2, '0')}
              </div>
            </div>
          ))}
        </div>
        <div className="text-sm text-gray-600 text-center">
          Hourly Average Wait Times (hover for details)
        </div>
      </div>
    );
  };

  const ZonePerformanceCard = ({ zone }) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-blue-500" />
            <span className="font-medium">{zone.zone_name}</span>
          </div>
          <Badge 
            variant="secondary"
            className={`${getDelayStatusColor(zone.delay_percentage)} text-white`}
          >
            {zone.delay_percentage}% delayed
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-600">Trips</div>
            <div className="font-semibold">{formatNumber(zone.trip_count)}</div>
          </div>
          <div>
            <div className="text-gray-600">Avg Wait</div>
            <div className="font-semibold">{zone.avg_wait_time}min</div>
          </div>
        </div>
        <Progress 
          value={Math.min((zone.avg_wait_time / 20) * 100, 100)} 
          className="mt-3"
        />
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700">Loading Analytics Dashboard...</h2>
          <p className="text-gray-500 mt-2">Processing taxi trip data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                🚕 NYC Taxi Analytics
              </h1>
              <p className="text-gray-600 text-lg">
                Real-time insights into ride-hailing delays and performance
              </p>
            </div>
            <div className="flex gap-3">
              {!dataLoaded && (
                <Button onClick={loadData} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
                  <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  Load Sample Data
                </Button>
              )}
              <Button 
                variant="outline" 
                onClick={fetchAnalytics}
                disabled={loading}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Refresh Analytics
              </Button>
            </div>
          </div>
        </div>

        {analytics ? (
          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">KPI Overview</TabsTrigger>
              <TabsTrigger value="patterns">Time Patterns</TabsTrigger>
              <TabsTrigger value="zones">Zone Analysis</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="hover:shadow-lg transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Trips</CardTitle>
                    <Car className="h-4 w-4 text-blue-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatNumber(analytics.total_trips)}</div>
                    <p className="text-xs text-muted-foreground">
                      Active ride requests processed
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Avg Trip Duration</CardTitle>
                    <Clock className="h-4 w-4 text-green-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{analytics.avg_trip_duration}min</div>
                    <p className="text-xs text-muted-foreground">
                      From pickup to dropoff
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Average Fare</CardTitle>
                    <DollarSign className="h-4 w-4 text-yellow-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(analytics.avg_fare)}</div>
                    <p className="text-xs text-muted-foreground">
                      Per trip before tips
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Delay Rate</CardTitle>
                    <AlertTriangle className={`h-4 w-4 ${analytics.delay_percentage > 20 ? 'text-red-500' : 'text-green-500'}`} />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{analytics.delay_percentage}%</div>
                    <p className="text-xs text-muted-foreground">
                      Trips with >10min wait
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Revenue and Performance Cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-green-500" />
                      Revenue Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="text-3xl font-bold text-green-600">
                          {formatCurrency(analytics.total_revenue)}
                        </div>
                        <div className="text-sm text-gray-600">Total Revenue Generated</div>
                      </div>
                      <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                        <div>
                          <div className="text-lg font-semibold">{formatNumber(analytics.delayed_trips_count)}</div>
                          <div className="text-sm text-gray-600">Delayed Trips</div>
                        </div>
                        <div>
                          <div className="text-lg font-semibold">{analytics.avg_wait_time}min</div>
                          <div className="text-sm text-gray-600">Avg Wait Time</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Users className="w-5 h-5 text-blue-500" />
                      Service Quality Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm">On-Time Performance</span>
                          <span className="text-sm font-semibold">
                            {(100 - analytics.delay_percentage).toFixed(1)}%
                          </span>
                        </div>
                        <Progress value={100 - analytics.delay_percentage} className="h-2" />
                      </div>
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm">Wait Time Efficiency</span>
                          <span className="text-sm font-semibold">
                            {Math.max(0, 100 - (analytics.avg_wait_time * 5)).toFixed(0)}%
                          </span>
                        </div>
                        <Progress 
                          value={Math.max(0, 100 - (analytics.avg_wait_time * 5))} 
                          className="h-2" 
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="patterns" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>24-Hour Wait Time Patterns</CardTitle>
                  <CardDescription>
                    Average pickup wait times throughout the day. Red triangles indicate high delay periods.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <HourlyChart data={hourlyData} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Peak Hour Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {hourlyData
                      .sort((a, b) => b.avg_wait_time - a.avg_wait_time)
                      .slice(0, 3)
                      .map((hour, index) => (
                        <div 
                          key={hour.hour} 
                          className={`p-4 rounded-lg border-2 ${
                            index === 0 ? 'border-red-200 bg-red-50' : 
                            index === 1 ? 'border-yellow-200 bg-yellow-50' : 
                            'border-orange-200 bg-orange-50'
                          }`}
                        >
                          <div className="text-center">
                            <div className="text-2xl font-bold">
                              {hour.hour.toString().padStart(2, '0')}:00
                            </div>
                            <div className="text-sm text-gray-600 mb-2">
                              {index === 0 ? 'Highest' : index === 1 ? '2nd Highest' : '3rd Highest'} Wait Time
                            </div>
                            <div className="text-lg font-semibold">{hour.avg_wait_time}min</div>
                            <div className="text-sm">
                              {hour.trip_count} trips • {hour.delay_percentage}% delayed
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="zones" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Top Delay Hotspots</CardTitle>
                  <CardDescription>
                    Pickup zones with highest delay rates and wait times
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {zoneData
                      .sort((a, b) => b.delay_percentage - a.delay_percentage)
                      .slice(0, 9)
                      .map((zone) => (
                        <ZonePerformanceCard key={zone.location_id} zone={zone} />
                      ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        ) : (
          <div className="text-center py-12">
            <Car className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No Data Available</h3>
            <p className="text-gray-500 mb-4">Click "Load Sample Data" to generate taxi trip analytics</p>
            <Button onClick={loadData} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Load Sample Data
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;