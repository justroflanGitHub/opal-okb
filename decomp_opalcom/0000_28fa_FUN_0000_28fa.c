
void FUN_0000_28fa(void)

{
  byte *pbVar1;
  byte *pbVar2;
  byte in_AH;
  int in_CX;
  byte *pbVar3;
  byte *unaff_SI;
  byte *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  int in_stack_00000000;
  
  while( true ) {
    do {
      pbVar1 = unaff_SI;
      unaff_SI = unaff_SI + 1;
      pbVar2 = unaff_DI;
      unaff_DI = unaff_DI + 1;
      *pbVar2 = (((*pbVar1 ^ in_AH) >> (in_AH & 7) | (*pbVar1 ^ in_AH) << 8 - (in_AH & 7)) ^ 0x5a) -
                (in_AH ^ 0x53) ^ 0xc5;
      in_AH = in_AH - 7;
      in_CX = in_CX + -1;
    } while (in_CX != 0);
    if (in_stack_00000000 + -1 == 0) break;
    pbVar3 = (byte *)(in_stack_00000000 + -2);
    FUN_0100_17d6();
    unaff_SI = pbVar3 + 1;
    in_AH = *pbVar3;
    unaff_DI = pbVar3 + 1;
    *pbVar3 = in_AH;
    in_CX = 0x5f;
    in_stack_00000000 = in_stack_00000000 + -1;
  }
  return;
}

