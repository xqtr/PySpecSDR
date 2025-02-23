def decode_ax25_frame(bit_stream):
    """
    Decode AX.25 frame from bit stream
    Returns decoded packet or None if invalid
    """
    try:
        # Find flag pattern (01111110)
        flag = [0, 1, 1, 1, 1, 1, 1, 0]
        
        # Find start and end flags
        start = -1
        for i in range(len(bit_stream) - 7):
            if bit_stream[i:i+8] == flag:
                start = i + 8
                break
                
        if start == -1:
            return None
            
        # Extract data between flags
        frame_bits = []
        ones_count = 0
        i = start
        
        while i < len(bit_stream) - 7:
            bit = bit_stream[i]
            frame_bits.append(bit)
            
            if bit == 1:
                ones_count += 1
            else:
                ones_count = 0
                
            # Skip stuffed bits
            if ones_count == 5 and i + 1 < len(bit_stream) and bit_stream[i+1] == 0:
                i += 2
                ones_count = 0
                continue
                
            i += 1
            
            # Check for end flag
            if frame_bits[-8:] == flag:
                frame_bits = frame_bits[:-8]
                break
                
        # Convert bits to bytes
        frame_bytes = []
        for i in range(0, len(frame_bits), 8):
            if i + 8 <= len(frame_bits):
                byte = 0
                for j in range(8):
                    byte |= frame_bits[i+j] << j
                frame_bytes.append(byte)
                
        return decode_aprs_payload(frame_bytes)
        
    except Exception:
        return None

def decode_aprs_payload(frame_bytes):
    """
    Decode APRS packet payload
    """
    try:
        if len(frame_bytes) < 14:  # Minimum length for valid packet
            return None
            
        # Extract addresses
        dest = ''.join([chr((b >> 1) & 0x7F) for b in frame_bytes[0:6]]).strip()
        source = ''.join([chr((b >> 1) & 0x7F) for b in frame_bytes[7:13]]).strip()
        
        # Control and PID fields
        ctrl = frame_bytes[13]
        pid = frame_bytes[14] if len(frame_bytes) > 14 else None
        
        # Information field
        info = ''
        if len(frame_bytes) > 15:
            info = ''.join([chr(b) for b in frame_bytes[15:]])
            
        return f"{source}>{dest}:{info}"
        
    except Exception:
        return None

