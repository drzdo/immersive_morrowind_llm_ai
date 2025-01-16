local config = require("zdo_immersive_morrowind_ai.config")
local util = require("zdo_immersive_morrowind_ai.common.util")

local socket = require("socket")
local bit = require("bit")

local this = {}

local state_disconnected = 'disconnected'
local state_connecting = 'connecting'
local state_active = 'active'

this.state = state_disconnected
this.tcp = nil
this.events_to_produce = {}
this.next_event_id = 1
this.connection_maintaining_loop_started = false

function this.produce_event_from_game(e)
    if this.state ~= state_active then
        util.debug("Skip producing event because not connected to the server")
        return
    end

    e["event_id"] = this.next_event_id
    this.next_event_id = this.next_event_id + 1

    table.insert(this.events_to_produce, e)
end

function this.produce_response_event(e_request, e_response)
    e_response["response_to_event_id"] = e_request["event_id"]
    this.produce_event_from_game(e_response)
end

function this.disconnect()
    if this.state ~= state_disconnected then
        util.log("Disconnecting")
        tes3ui.showNotifyMenu("Disconnected from the RPG AI server")

        this.state = state_disconnected
        this.tcp:close()
        this.tcp = nil
    end
end

function this.pack_be_uint32(int_value)
    -- 0x00112233
    --   ^^=b3
    --         ^^=b0

    local b0 = bit.band(int_value, 0x000000ff)
    local b1 = bit.rshift(bit.band(int_value, 0x0000ff00), 8)
    local b2 = bit.rshift(bit.band(int_value, 0x00ff0000), 16)
    local b3 = bit.rshift(bit.band(int_value, 0xff000000), 24)
    local packed = string.char(b3) .. string.char(b2) .. string.char(b1) .. string.char(b0)
    return packed
end

function this.unpack_be_uint32(packed)
    local b0 = string.byte(packed, 4, 4)
    local b1 = string.byte(packed, 3, 3)
    local b2 = string.byte(packed, 2, 2)
    local b3 = string.byte(packed, 1, 1)
    local int_value = b0 + bit.lshift(b1, 8) + bit.lshift(b2, 16) + bit.lshift(b3, 24)
    return int_value
end

function this.run_producer()
    timer.start({
        duration = 1.0 / 30.0,
        type = timer.real,
        iterations = -1,
        persist = false,
        callback = function(e)
            if this.state ~= state_active then
                util.log("Cancel send timer")
                e.timer:cancel()
                return
            end

            for _, e in pairs(this.events_to_produce) do
                local payload = json.encode(e)
                util.debug("Publishing '%s'", payload)

                local size = string.len(payload)
                local size_encoded = this.pack_be_uint32(size)
                util.debug("size=%d", size)

                local index_of_last_byte_sent, status = this.tcp:send(size_encoded)
                if index_of_last_byte_sent == nil then
                    util.log("Expected 4 bytes to get sent: %s", status)
                    this.disconnect()
                    return
                end

                this.tcp:send(payload)
                util.debug("Sent")
            end

            this.events_to_produce = {}
        end
    })
end

function this.run_consumer()
    local expecting_header = true
    local receiving_buf_expected_size = 4
    local receiving_buf = ''

    timer.start({
        duration = 1.0 / 30.0,
        type = timer.real,
        iterations = -1,
        persist = false,
        callback = function(e)
            if this.state ~= state_active then
                util.log("Cancel receive timer")
                e.timer:cancel()
                return
            end

            local result, status, partial = this.tcp:receive(receiving_buf_expected_size - string.len(receiving_buf))
            -- util.debug("Receive result %s %s", result, status)
            if result == nil then
                if status == 'timeout' then
                    receiving_buf = receiving_buf .. partial
                else
                    util.log("Failed to receive header: %s", status)
                    this.disconnect()
                    return
                end
            else
                receiving_buf = receiving_buf .. result
            end

            if receiving_buf_expected_size == string.len(receiving_buf) then
                util.debug("Expected buf size is %d", receiving_buf_expected_size)
                util.debug("Actually received buf size %d", string.len(receiving_buf))

                if expecting_header then
                    local len = this.unpack_be_uint32(receiving_buf)
                    util.debug("Received header, size=%d", len)

                    receiving_buf_expected_size = len
                    receiving_buf = ''
                    expecting_header = false
                else
                    util.debug("Received message: %s", receiving_buf)
                    local e = json.decode(receiving_buf)
                    event.trigger("zdo_ai_rpg:event_from_server", e)

                    receiving_buf_expected_size = 4
                    receiving_buf = ''
                    expecting_header = true
                end
            end
        end
    })
end

function this.connect()
    if this.state ~= state_disconnected then
        util.log("Skip connecting as not in disconnected state")
        return
    end

    this.state = state_connecting

    this.tcp = socket.tcp()

    local host = config.server_host
    local port = tonumber(config.server_port)

    util.log("Connecting to %s:%d...", host, port)
    tes3ui.showNotifyMenu(util.i18n("connecting"))

    timer.delayOneFrame(function()
        local status, error = this.tcp:connect(host, port)

        if status == 1 then
            this.state = state_active
            this.events_to_send = {}

            this.tcp:settimeout(0, 'b')
            this.tcp:settimeout(0, 't')

            util.log("Connected")
            tes3ui.showNotifyMenu(util.i18n("connected"))

            util.log("Running consumer and producer...")
            this.run_consumer()
            this.run_producer()
            util.log("Event bus is initialized")

            this.produce_event_from_game({
                data = {
                    type = "game_loaded"
                }
            })
        else
            this.state = state_disconnected
            util.log("Failed to connect: %s", error)
        end
    end, timer.real)
end

function this.run_connection_maintaining_loop()
    -- if this.connection_maintaining_loop_started then
    --     return
    -- end

    if this.state == state_disconnected then
        util.log("Trying to autoconnect")
        this.connect()
    end

    timer.start({
        duration = 10,
        type = timer.real,
        iterations = -1,
        persist = false,
        callback = function(e)
            this.connection_maintaining_loop_started = true

            if not config.auto_reconnect then
                return
            end

            if this.state == state_disconnected then
                util.log("Trying to autoconnect")
                this.connect()
            end
        end
    })
end

return this
