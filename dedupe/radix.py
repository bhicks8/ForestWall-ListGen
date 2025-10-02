import pytricia
import ipaddress

def test():
    pt = pytricia.PyTricia()
    pt.insert("192.168.1.0/24", "local network")

    if not "192.168.1.0/20" in pt:
        # Add a new prefix, and remove any existing prefixes that are covered by it
        pt.insert("192.168.1.0/20", "local network")
        children = pt.children("192.168.1.0/20")
        for child in children:
            pt.remove(child)

def parse_cidr(cidr):
    try:
        if "/" in cidr:
            return ipaddress.ip_network(cidr, strict=False)
        else:
            # Assume a single IP address, convert to /32 or /128 CIDR
            ip = ipaddress.ip_address(cidr)
            if ip.version == 4:
                return ipaddress.ip_network(f"{cidr}/32", strict=False)
            else:
                return ipaddress.ip_network(f"{cidr}/128", strict=False)
    except ValueError:
        raise ValueError(f"Invalid CIDR notation: {cidr}")

class RadixDedupe:
    """
    A deduplication class using a radix tree to track seen CIDR blocks.
    """
    def __init__(self):
        self.pt_v4 = pytricia.PyTricia(32)
        self.pt_v6 = pytricia.PyTricia(128)

    def __len__(self):
        return len(self.pt_v4) + len(self.pt_v6)

    def __get_radix__(self, net):
        if net.version == 4:
            return self.pt_v4
        else:
            return self.pt_v6
        
    def addMany(self, cidrs):
        for cidr in cidrs:
            self.add(cidr)

    def add(self, cidr):
        net = parse_cidr(cidr)
        pt = self.__get_radix__(net)

        # Check if the CIDR or any encompassing CIDR is already present
        if net in pt:
            return False
        
        # Insert and remove any existing CIDRs that are encompassed by the new CIDR
        pt.insert(net, True)
        for child in pt.children(net):
            pt.delete(child)

        return True
    
    def remove(self, cidr):
        net = parse_cidr(cidr)
        pt = self.__get_radix__(net)
        pt.delete(cidr)

    def contains(self, cidr):
        net = parse_cidr(cidr)
        pt = self.__get_radix__(net)
        return cidr in pt

    def all(self):
        return sorted(list(self.pt_v4.keys()) + list(self.pt_v6.keys()))

    def reset(self):
        self.pt_v4 = pytricia.PyTricia(32)
        self.pt_v6 = pytricia.PyTricia(128)