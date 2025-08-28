import streamlit as st
from collections import defaultdict

class TablePlanner:
    def __init__(self):
        # Tables: {table_id: {'capacity': capacity, 'occupied': bool, 'room': room_name}}
        self.tables = {}
        # Current assignments: {table_id: [group_ids]}
        self.assignments = defaultdict(list)
        # Guest groups waiting to be seated: {group_id: {'size': size, 'name': name}}
        self.groups = {}
        # Seated groups: {group_id: {'size': size, 'name': name, 'table': table_id}}
        self.seated_groups = {}
        # Counter for group IDs
        self.next_group_id = 1
        # Combined tables tracking
        self.combined_tables = {}
        # Room definitions
        self.rooms = {
            "GREENROOM": ["T1A", "T1B", "T2", "T3A", "T3B"],
            "RESTAURANT": ["T4", "T5", "T6", "T7", "T8", "T9A", "T9B"],
            "BOTTOM BAR": ["WINDOW", "BACK RIGHT", "LADS", "BLACKBOARD"],
            "SMALL FUNCTION": ["SQUARE", "OVAL", "WOODEN"]
        }

    def add_table(self, table_id, capacity, room):
        """Add a new table to the pub"""
        self.tables[table_id] = {'capacity': capacity, 'occupied': False, 'combined': False, 'room': room}

    def remove_table(self, table_id):
        """Remove a table from the pub"""
        if table_id in self.tables:
            del self.tables[table_id]
            if table_id in self.assignments:
                # Move any assigned groups back to waiting
                for group_id in self.assignments[table_id]:
                    if group_id in self.seated_groups:
                        # Move seated group back to waiting
                        group_data = self.seated_groups[group_id]
                        self.groups[group_id] = {'size': group_data['size'], 'name': group_data['name']}
                        del self.seated_groups[group_id]
                del self.assignments[table_id]

    def add_guests(self, group_size, group_name=None):
        """Add a new group of guests"""
        group_id = self.next_group_id
        self.next_group_id += 1
        
        # If no name provided, use the ID
        if not group_name:
            group_name = f"Group {group_id}"
            
        self.groups[group_id] = {'size': group_size, 'name': group_name}
        return group_id

    def seat_guests(self, group_id, table_id):
        """Seat a specific group at a specific table"""
        if table_id not in self.tables:
            return False, "Table does not exist"

        if group_id not in self.groups:
            return False, "Group does not exist"

        group_size = self.groups[group_id]['size']
        group_name = self.groups[group_id]['name']
        table_info = self.tables[table_id]

        # Check if table is part of a combined table
        if table_info.get('combined', False) and '+' in table_id:
            # This is a combined table, use its capacity
            table_capacity = table_info['capacity']
        else:
            # Regular table
            table_capacity = table_info['capacity']

        if group_size > table_capacity:
            return False, "Group too large for table"

        # Check if table is already occupied
        if self.tables[table_id]['occupied']:
            # Check if there's enough remaining capacity
            current_occupancy = sum(
                self.seated_groups[gid]['size'] for gid in self.assignments[table_id] 
                if gid in self.seated_groups
            )
            if current_occupancy + group_size > table_capacity:
                return False, "Not enough space at table"

        # Seat the group
        self.assignments[table_id].append(group_id)
        self.tables[table_id]['occupied'] = True
        
        # Move group from waiting to seated
        self.seated_groups[group_id] = {
            'size': group_size,
            'name': group_name,
            'table': table_id
        }
        del self.groups[group_id]

        return True, "Group seated successfully"

    def mark_group_left(self, group_id):
        """Mark a group as having left the pub"""
        if group_id in self.seated_groups:
            table_id = self.seated_groups[group_id]['table']
            
            # Remove group from table assignments
            if table_id in self.assignments and group_id in self.assignments[table_id]:
                self.assignments[table_id].remove(group_id)
                
                # If no more groups at table, mark as unoccupied
                if not self.assignments[table_id]:
                    self.tables[table_id]['occupied'] = False
                    
                    # If this is a combined table, break it apart
                    if '+' in table_id and table_id in self.combined_tables:
                        component_tables = self.combined_tables[table_id]
                        for comp_table in component_tables:
                            if comp_table in self.tables:
                                self.tables[comp_table]['occupied'] = False
                                self.tables[comp_table]['combined'] = False
                        # Remove the combined table
                        del self.tables[table_id]
                        del self.combined_tables[table_id]
                        del self.assignments[table_id]
            
            # Remove group from seated groups
            del self.seated_groups[group_id]
            return True, f"Group marked as left"
        else:
            return False, "Group not found or not seated"

    def find_best_table_for_group(self, group_size, group_id):
        """Find the best table for a group, combining tables if necessary"""
        # First try to find a single table that can accommodate the group
        for table_id, table_info in self.tables.items():
            # Skip combined tables and tables that are already part of a combination
            if '+' in table_id or table_info.get('combined', False) or table_info['occupied']:
                continue
                
            if group_size <= table_info['capacity']:
                return table_id, False, None
        
        # If no single table found, try to combine tables in the same room
        # Group empty tables by room
        empty_tables_by_room = {}
        for table_id, table_info in self.tables.items():
            # Skip tables that are already part of a combined table
            if '+' in table_id or table_info.get('combined', False) or table_info['occupied']:
                continue
                
            room = table_info['room']
            if room not in empty_tables_by_room:
                empty_tables_by_room[room] = []
            empty_tables_by_room[room].append((table_id, table_info['capacity']))
        
        # For each room, try to find a combination of tables that can accommodate the group
        for room, empty_tables in empty_tables_by_room.items():
            # Sort tables by capacity (largest first)
            empty_tables.sort(key=lambda x: x[1], reverse=True)
            
            # Try to find a combination of tables that can accommodate the group
            for i in range(len(empty_tables)):
                current_sum = 0
                combined_tables = []
                
                for j in range(i, len(empty_tables)):
                    table_id, capacity = empty_tables[j]
                    current_sum += capacity
                    combined_tables.append(table_id)
                    
                    if current_sum >= group_size:
                        # Mark these tables as combined and occupied
                        for table_id in combined_tables:
                            self.tables[table_id]['combined'] = True
                            self.tables[table_id]['occupied'] = True
                        
                        # Create a virtual combined table
                        combined_id = "+".join(combined_tables)
                        combined_capacity = current_sum
                        self.tables[combined_id] = {
                            'capacity': combined_capacity,
                            'occupied': True,
                            'combined': True,
                            'component_tables': combined_tables,
                            'room': room
                        }
                        
                        # Track the combined table
                        self.combined_tables[combined_id] = combined_tables
                        
                        # Add the group to the combined table
                        self.assignments[combined_id] = []
                        
                        return combined_id, True, combined_tables
        
        return None, False, None

    def optimize_seating(self):
        """Optimize the seating arrangement for maximum efficiency"""
        # Create a copy of groups to avoid modification during iteration
        groups_to_seat = list(self.groups.items())
        
        # Sort groups by size (descending) for most efficient packing
        groups_to_seat.sort(key=lambda x: x[1]['size'], reverse=True)
        
        # Try to assign each group to a table
        for group_id, group_data in groups_to_seat:
            if group_id not in self.groups:  # Skip if already seated
                continue
                
            group_size = group_data['size']
            group_name = group_data['name']
            
            # Find the best table for this group
            table_id, is_combined, combined_tables = self.find_best_table_for_group(group_size, group_id)
            
            if table_id:
                # Seat the group at the table
                self.assignments[table_id].append(group_id)
                self.tables[table_id]['occupied'] = True
                
                # Move group from waiting to seated
                self.seated_groups[group_id] = {
                    'size': group_size,
                    'name': group_name,
                    'table': table_id
                }
                
                # Remove group from waiting list
                del self.groups[group_id]
                
                # Log if tables were combined
                if is_combined:
                    st.session_state.messages.append(f"Combined tables {combined_tables} in {self.tables[table_id]['room']} for {group_name}")

    def get_table_utilization(self, table_id):
        """Get utilization percentage for a table"""
        if table_id not in self.tables:
            return 0

        capacity = self.tables[table_id]['capacity']
        if capacity == 0:
            return 0

        # Calculate occupancy for all assigned groups
        occupancy = sum(
            self.seated_groups[gid]['size'] for gid in self.assignments[table_id] 
            if gid in self.seated_groups
        )
        
        return (occupancy / capacity) * 100 if capacity > 0 else 0

    def get_overall_utilization(self):
        """Get overall utilization percentage for all tables"""
        total_capacity = sum(table['capacity'] for table in self.tables.values())
        if total_capacity == 0:
            return 0

        total_occupancy = 0
        for table_id in self.tables:
            # Calculate occupancy for all assigned groups
            total_occupancy += sum(
                self.seated_groups[gid]['size'] for gid in self.assignments[table_id] 
                if gid in self.seated_groups
            )
        
        return (total_occupancy / total_capacity) * 100 if total_capacity > 0 else 0

    def get_room_for_table(self, table_id):
        """Get the room for a given table"""
        for room, tables in self.rooms.items():
            if table_id in tables:
                return room
        return "Unknown"

    def get_table_status(self):
        """Get status of all tables for display"""
        table_status = []
        for table_id in sorted(self.tables.keys()):
            capacity = self.tables[table_id]['capacity']
            room = self.tables[table_id].get('room', 'Unknown')
            groups = self.assignments[table_id]
            
            # Calculate occupancy for all assigned groups
            occupancy = 0
            group_names = []
            for group_id in groups:
                if group_id in self.seated_groups:
                    occupancy += self.seated_groups[group_id]['size']
                    group_names.append(f"{self.seated_groups[group_id]['name']}({self.seated_groups[group_id]['size']})")
            
            utilization = self.get_table_utilization(table_id)
            
            # Add indicator for combined tables
            table_type = " (Combined)" if '+' in table_id or self.tables[table_id].get('combined', False) else ""
            
            group_list = ", ".join(group_names)
            status = f"Table {table_id}{table_type} ({room}, Capacity: {capacity}): {group_list} | Occupancy: {occupancy}/{capacity} ({utilization:.1f}%)"
            table_status.append(status)
        
        return table_status
    
    def get_waiting_groups(self):
        """Get waiting groups for display"""
        waiting_groups = []
        for group_id, group_data in self.groups.items():
            waiting_groups.append(f"{group_data['name']}: {group_data['size']} people")
        
        return waiting_groups
    
    def rename_group(self, group_id, new_name):
        """Rename a group"""
        if group_id in self.groups:
            self.groups[group_id]['name'] = new_name
            return True
        elif group_id in self.seated_groups:
            self.seated_groups[group_id]['name'] = new_name
            return True
        return False
    
    def get_all_groups(self):
        """Get all groups (both waiting and seated) for display"""
        all_groups = []
        
        # Add waiting groups
        for group_id, group_data in self.groups.items():
            all_groups.append({
                'id': group_id,
                'name': group_data['name'],
                'size': group_data['size'],
                'status': 'Waiting',
                'table': None
            })
        
        # Add seated groups
        for group_id, group_data in self.seated_groups.items():
            all_groups.append({
                'id': group_id,
                'name': group_data['name'],
                'size': group_data['size'],
                'status': 'Seated',
                'table': group_data['table']
            })
        
        return all_groups


# Initialize the table planner in session state
if 'planner' not in st.session_state:
    st.session_state.planner = TablePlanner()
    
    # Add default tables with room information
    # GREENROOM
    st.session_state.planner.add_table("T1A", 2, "GREENROOM")
    st.session_state.planner.add_table("T1B", 2, "GREENROOM")
    st.session_state.planner.add_table("T2", 4, "GREENROOM")
    st.session_state.planner.add_table("T3A", 6, "GREENROOM")
    st.session_state.planner.add_table("T3B", 4, "GREENROOM")

    # RESTAURANT
    st.session_state.planner.add_table("T4", 4, "RESTAURANT")
    st.session_state.planner.add_table("T5", 4, "RESTEAUANT")
    st.session_state.planner.add_table("T6", 4, "RESTAURANT")
    st.session_state.planner.add_table("T7", 4, "RESTAURANT")
    st.session_state.planner.add_table("T8", 4, "RESTAURANT")
    st.session_state.planner.add_table("T9A", 2, "RESTAURANT")
    st.session_state.planner.add_table("T9B", 2, "RESTAURANT")

    # BOTTOM BAR
    st.session_state.planner.add_table("WINDOW", 6, "BOTTOM BAR")
    st.session_state.planner.add_table("BACK RIGHT", 2, "BOTTOM BAR")
    st.session_state.planner.add_table("LADS", 4, "BOTTOM BAR")
    st.session_state.planner.add_table("BLACKBOARD", 4, "BOTTOM BAR")
    
    # SMALL FUNCTION ROOM
    st.session_state.planner.add_table("SQUARE", 2, "SMALL FUNCTION")
    st.session_state.planner.add_table("OVAL", 6, "SMALL FUNCTION")
    st.session_state.planner.add_table("WOODEN", 8, "SMALL FUNCTION")

# Streamlit app layout
st.title("🍻 Pub Table Planner")
st.markdown("---")

# Initialize message log in session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Function to add messages to log
def log_message(message):
    st.session_state.messages.append(message)
    if len(st.session_state.messages) > 10:  # Keep only the last 10 messages
        st.session_state.messages.pop(0)

# Create tabs for different functionalities
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "Table Management", "Guest Management", "Manual Assignment", "Group Management"])

with tab1:
    st.header("Current Status")
    
    # Display overall utilization
    utilization = st.session_state.planner.get_overall_utilization()
    st.metric("Overall Utilization", f"{utilization:.1f}%")
    
    # Display table status
    st.subheader("Table Status")
    table_status = st.session_state.planner.get_table_status()
    for status in table_status:
        st.text(status)
    
    # Display waiting groups
    st.subheader("Waiting Groups")
    waiting_groups = st.session_state.planner.get_waiting_groups()
    if waiting_groups:
        for group in waiting_groups:
            st.text(group)
    else:
        st.info("No groups waiting to be seated")
    
    # Optimize button
    if st.button("Optimize Seating", use_container_width=True):
        st.session_state.planner.optimize_seating()
        log_message("Optimized seating arrangement for maximum efficiency")
        st.rerun()

with tab2:
    st.header("Table Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add Table")
        table_id = st.text_input("Table ID", key="add_table_id")
        capacity = st.number_input("Capacity", min_value=1, value=4, key="add_capacity")
        room = st.selectbox("Room", options=["GREENROOM", "RESTAURANT", "BOTTOM BAR", "SMALL FUNCTION"], key="add_room")
        if st.button("Add Table"):
            if table_id:
                if table_id not in st.session_state.planner.tables:
                    st.session_state.planner.add_table(table_id, capacity, room)
                    log_message(f"Added table {table_id} with capacity {capacity} to {room}")
                    st.rerun()
                else:
                    st.error(f"Table {table_id} already exists")
            else:
                st.error("Please provide a table ID")
    
    with col2:
        st.subheader("Remove Table")
        remove_table_id = st.selectbox(
            "Select Table to Remove",
            options=list(st.session_state.planner.tables.keys()),
            key="remove_table_select"
        )
        if st.button("Remove Table", type="primary"):
            if remove_table_id in st.session_state.planner.tables:
                st.session_state.planner.remove_table(remove_table_id)
                log_message(f"Removed table {remove_table_id}")
                st.rerun()
            else:
                st.error(f"Table {remove_table_id} does not exist")

with tab3:
    st.header("Guest Management")
    
    st.subheader("Add Group")
    group_name = st.text_input("Group Name (optional)", key="group_name")
    group_size = st.number_input("Group Size", min_value=1, value=2, key="group_size")
    if st.button("Add Group"):
        group_id = st.session_state.planner.add_guests(group_size, group_name)
        if group_name:
            log_message(f"Added {group_name} with {group_size} people")
        else:
            log_message(f"Added group {group_id} with {group_size} people")
        st.rerun()

with tab4:
    st.header("Manual Assignment")
    
    if st.session_state.planner.groups:
        group_options = {
            f"{group_data['name']} ({group_data['size']} people)": gid 
            for gid, group_data in st.session_state.planner.groups.items()
        }
        selected_group_label = st.selectbox("Select Group", options=list(group_options.keys()))
        selected_group_id = group_options[selected_group_label]
    else:
        st.info("No groups available for assignment")
        selected_group_id = None
    
    # Only show regular tables (not combined ones) for manual assignment
    table_options = [tid for tid in st.session_state.planner.tables.keys() if '+' not in tid and not st.session_state.planner.tables[tid].get('combined', False)]
    selected_table = st.selectbox("Select Table", options=table_options)
    
    if st.button("Assign Group to Table") and selected_group_id is not None:
        success, message = st.session_state.planner.seat_guests(selected_group_id, selected_table)
        log_message(message)
        st.rerun()

with tab5:
    st.header("Group Management")
    
    # Display all groups (both waiting and seated)
    st.subheader("All Groups")
    
    # Get all groups
    all_groups = st.session_state.planner.get_all_groups()
    
    if all_groups:
        # Display groups in a table format
        for group in all_groups:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.text(group['name'])
            with col2:
                st.text(f"{group['size']} people")
            with col3:
                st.text(group['status'])
            with col4:
                if group['table']:
                    st.text(f"Table {group['table']}")
                else:
                    st.text("")
                
            # Add action buttons for each group
            col5, col6, col7 = st.columns([2, 2, 1])
            with col5:
                # Rename functionality
                new_name = st.text_input("Rename", value=group['name'], key=f"rename_{group['id']}")
            with col6:
                if st.button("Rename", key=f"rename_btn_{group['id']}"):
                    if st.session_state.planner.rename_group(group['id'], new_name):
                        log_message(f"Renamed group to {new_name}")
                        st.rerun()
            with col7:
                # Mark as left button for seated groups
                if group['status'] == 'Seated':
                    if st.button("Mark Left", key=f"left_{group['id']}"):
                        success, message = st.session_state.planner.mark_group_left(group['id'])
                        log_message(message)
                        st.rerun()
    else:
        st.info("No groups yet")

# Display message log
st.markdown("---")
st.subheader("Message Log")
for message in st.session_state.messages:
    st.text(message)

# Add some styling
st.markdown("""
<style>
    .stMetric {
        background-color: #0e1117;
        border: 1px solid #262730;
        padding: 10px;
        border-radius: 5px;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)
