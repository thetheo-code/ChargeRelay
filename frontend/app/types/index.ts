export interface Vehicle {
  id: number
  name: string
  id_tag: string | null
  image_data: string | null
  created_at: string
}

export interface MeterValue {
  measurand: string
  value: string
  unit: string
  timestamp: string
}

export interface ActiveSession {
  session_id: number
  connector_id: number
  transaction_id: number | null
  id_tag: string
  start_time: string
  start_meter_wh: number | null
  charge_point_id: string
  model: string | null
  vendor: string | null
  duration_seconds: number | null
  latest_meter_values: MeterValue[]
  vehicle_id: number | null
  vehicle_name: string | null
}

export interface Session {
  session_id: number
  connector_id: number
  transaction_id: number | null
  id_tag: string
  start_time: string
  stop_time: string | null
  start_meter_wh: number | null
  stop_meter_wh: number | null
  energy_kwh: number | null
  stop_reason: string | null
  charge_point_id: string
  model: string | null
  vendor: string | null
  vehicle_id: number | null
  vehicle_name: string | null
}
